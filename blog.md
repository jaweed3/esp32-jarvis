# RescueVision Edge — Engineering Blog

## Overview

Deploying YOLOv8n INT8 (3.4M params, 192×192) on ESP32-S3 for SAR victim detection. From reference kernels at 219s/inference to ESP-NN + LOGISTIC LUT at 7.2s (30.4× speedup). Here's every blocker we hit and how we fixed it.

---

## Phase 1: The Reference Nightmare (219s/inference)

### B1: Watchdog Timer Reset During AllocateTensors
**Symptom:** Device resets ~300ms into `MicroInterpreter::AllocateTensors()`.

**Root cause:** Task Watchdog Timer (TWDT/TG1 WDT) has a 300ms default timeout. `AllocateTensors()` iterates through all model ops, calling `Prepare()` on each, which triggers memory planning and scratch buffer allocation. On a 240 MHz single-core-active scenario, this exceeds 300ms.

**Fix:**
```cpp
esp_task_wdt_deinit();
esp_task_wdt_init(60, false);
esp_task_wdt_add(NULL);
```
Set WDT to 60s _before_ `AllocateTensors()`. Also feed WDT during long loops.

**Lesson:** Always deinit ESP TWDT early in `setup()` if you expect any operation >300ms.

### B2: Tensor Arena in PSRAM (Not .psram.data Section)
**Symptom:** TFLite Micro crashes during inference because tensor arena is in SRAM (too small) or misaligned.

**Root cause:** Default `malloc()` on ESP-IDF uses SRAM, not PSRAM. The 4MB tensor arena doesn't fit in 512KB SRAM.

**Fix:**
```cpp
uint8_t* tensor_arena = (uint8_t*)heap_caps_malloc(kTensorArenaSize, MALLOC_CAP_SPIRAM);
```
Not a section attribute — use `heap_caps_malloc()` explicitly with `MALLOC_CAP_SPIRAM`.

**Lesson:** Don't trust `malloc()` on ESP32-S3 for large buffers. Always use `heap_caps_malloc()` with explicit PSRAM caps.

### B3: Model Data Section Alignment
**Symptom:** Flash cache errors when accessing model data compiled as C array.

**Root cause:** The generated `model_data.h` C array needs proper alignment (4-byte for TFLite flatbuffer).

**Fix:** Use `__attribute__((aligned(8)))` on the model array declaration and ensure it's placed in flash (default `.drom0` section in ESP-IDF).

---

## Phase 2: ESP-NN Integration (12.2× Speedup to 18s)

### B4: ESP-NN Not Available as PlatformIO Library
**Symptom:** `#include <esp_nn.h>` → file not found.

**Root cause:** ESP-NN is not on PlatformIO's registry. Must be cloned manually.

**Fix:**
```bash
git clone https://github.com/espressif/esp-nn.git lib/esp-nn/
```
Then in `platformio.ini`:
```ini
build_flags = 
  -DESP_NN
  -DCONFIG_NN_OPTIMIZED
  -Ilib/esp-nn/include
  -Ilib/esp-nn/src/common
```

### B5: Missing common_functions.h
**Symptom:** Compiler error: `common_functions.h` not found (included by esp-nn headers).

**Root cause:** ESP-NN's internal headers reference `common_functions.h` from `src/common/` but this path isn't in the include chain.

**Fix:** Add `-Ilib/esp-nn/src/common` to `build_flags`.

### B6: ESP32-P4 RISC-V Assembly Incompatible with Xtensa
**Symptom:** Assembler errors when compiling ESP-NN source files:
```
Error: unknown instruction `vfmv.s.f`
```

**Root cause:** ESP-NN v1.2.3 includes ESP32-P4 (RISC-V) assembly files alongside Xtensa files. The Xtensa toolchain chokes on RISC-V instructions.

**Fix:** Delete all P4-specific files from the cloned repo:
```bash
find lib/esp-nn/src -name "*p4*" -o -name "*riscv*" | xargs rm
```

**Lesson:** ESP-NN is a multi-arch library. Always clean out irrelevant architectures.

### B7: Duplicate Symbols — Reference vs ESP-NN Kernels
**Symptom:** Linker error: `multiple definition of Register_CONV_2D()`.

**Root cause:** Both `lib/tflite-micro/.../kernels/conv.cc` (reference) and `lib/tflite-micro/.../kernels/esp_nn/conv.cc` (ESP-NN) define the same registration function. With `-DESP_NN`, the build system compiles both directories.

**Fix:** Delete all reference kernel `.cc` files that have `esp_nn/` counterparts:
```bash
# Delete reference kernels replaced by ESP-NN
rm conv.cc depthwise_conv.cc fully_connected.cc \
   pooling.cc softmax.cc add.cc mul.cc logistic.cc
```

**Affected ops:** Conv2D, DepthwiseConv2D, FullyConnected, AveragePool2D, MaxPool2D, Softmax, Add, Mul, Logistic.

### B8: TFLite Micro Source Structure Mismatch
**Symptom:** ESP-NN wrapper includes like `#include "tensorflow/lite/micro/kernels/esp_nn/..."` resolve to wrong paths.

**Root cause:** Our tflite-micro source tree cloned via PlatformIO has a different structure than what ESP-NN expects. The ESP-NN wrappers assume a specific include layout.

**Fix:** Manually created the full directory tree `lib/tflite-micro/tensorflow/lite/micro/kernels/esp_nn/` and placed our wrapper `.cc` files there. The PlatformIO `lib/tflite-micro/` library includes all subdirectories automatically.

### B9: MicroProfiler Returns All Zeros (EspSpecific)
**Symptom:** `MicroProfiler` shows 0µs for every op, even though inference takes 219s.

**Root cause:** TFLite Micro has two implementations of `GetCurrentTimeTicks()`:
1. `micro_time.cc` (generic) → returns 0 (stub)
2. `esp/micro_time.cc` (ESP-specific) → returns `esp_timer_get_time()` in µs

Both files exist in the source tree. The generic one is compiled first and overrides the ESP-specific one. The ESP-specific version correctly reads the ESP timer.

**Fix:**
```bash
# Disable the generic stub by renaming it
mv micro_time.cc micro_time.cc.bak
```
Now only `esp/micro_time.cc` is compiled, returning real microsecond timestamps.

**Lesson:** TFLite Micro's cross-platform timer abstraction has a priority bug — the generic stub takes precedence over platform-specific implementations.

---

## Phase 3: LOGISTIC Optimization (2.5× More to 7.2s)

### B10: Op Profiling Revealed Wrong Bottleneck Assumption
**Symptom:** We assumed non-ESP-NN ops (Reshape, Concat) were the bottleneck. Profiling showed the opposite.

**Fix:** Actually profile before optimizing. MicroProfiler showed:
```
LOGISTIC: 11,758 ms (62.3%)
CONV_2D:  6,634 ms (35.2%)
Other 12:   471 ms ( 2.5%)
```

**Lesson:** Don't guess the bottleneck. Profile first. Our intuition was completely wrong — LOGISTIC (a simple element-wise activation) was the dominant cost, not memory-bound ops.

### B11: GetScratchBuffer() Only Works During kInvoke, Not kPrepare
**Symptom:** `abort()` during `Prepare op 2 (code 14)` — LOGISTIC op.

**Backtrace:**
```
MicroInterpreterContext::GetScratchBuffer() at micro_interpreter_context.cc:70
  → TFLITE_DCHECK(state_ == InterpreterState::kInvoke)
esp_nn/logistic.cc:60 → Prepare() called GetScratchBuffer() during kPrepare
```

**Root cause:** We called `GetScratchBuffer()` in `Prepare()` to get the LUT pointer for `esp_nn_logistic_s8_prepare()`. But `GetScratchBuffer()` asserts `state_ == kInvoke`. During `Prepare`, state is `kPrepare`.

**Fix:** Defer LUT preparation to the first `Eval()` call:
```cpp
// In Prepare(): just request the scratch buffer, store params
context->RequestScratchBufferInArena(context, size, &data->buffer_idx);
data->input_scale = input->params.scale;
data->input_zero_point = input->params.zero_point;
data->lut_prepared = false;

// In first Eval(): get scratch buffer and prepare LUT
if (!data->lut_prepared && data->buffer_idx > -1) {
  int8_t* lut = context->GetScratchBuffer(context, data->buffer_idx);
  esp_nn_logistic_s8_prepare(lut, data->input_zero_point, data->input_scale);
  data->lut_prepared = true;
}
```

### B12: MicroProfiler Event Overflow — 4096 Limit
**Symptom:** After 16 inferences (~120s):
```
MicroProfiler errored out because total number of events exceeded the maximum of 4096.
```

**Root cause:** MicroProfiler allocates a fixed-size event buffer (4096 entries). Each op invocation per inference creates multiple profile events (MicroProfiler::Event). With 15 ops × 16 inferences, plus some ops generating multiple events, we hit the limit.

**Fix:** Remove MicroProfiler for production benchmarks after initial profiling is done, or increase the buffer size in the MicroProfiler configuration. For our use case, we run profiling only during the bottleneck analysis phase, then disable it for final timing.

---

## Phase 4: Paper & Infrastructure Blockers

### B13: PyTorch → TFLite FP32 mAP Drop (45.59% → 12.26%)
**Symptom:** Massive accuracy drop when converting from PyTorch to TFLite (even before INT8 quantization).

**Root cause:** The ONNX export path introduces numerical differences in operation kernel mapping, particularly in the detection head (convolution + reshape + sigmoid). Ultralytics' native inference and TFLite's evaluator use different post-processing pipelines.

**Current status:** This is a known pipeline fidelity issue. The TFLite FP32 (12.26%) is used as the reference baseline for all INT8 comparisons, but the gap from PyTorch (45.59%) is unexplained and too large to ignore for journal submission.

**Lesson:** Always validate TFLite FP32 output against PyTorch output on the same inputs before trusting the quantization pipeline.

### B14: Power Measurements — Model-Based Only (No INA219)
**Symptom:** All power figures are datasheet estimates, not empirical measurements.

**Root cause:** INA219 module exists but was not integrated before the measurement deadline. The ESP32-S3 datasheet provides typical current draw per subsystem, which we used for estimates.

**Impact:** Power claims are speculative. A journal reviewer will flag this.

### B15: Camera Not Integrated
**Symptom:** No end-to-end demo with real camera input. All benchmarks use synthetic data (memset 128).

**Root cause:** OV2640 camera initialization works (prints "Camera initialized: QVGA (320x240) JPEG"), but JPEG-to-RGB decoding and feeding real frames into the model pipeline wasn't implemented.

**Impact:** The "victim detection" claim cannot be demonstrated with real images.

### B16: No Comparison Platform
**Symptom:** Only PC GPU vs ESP32-S3. Missing RPi 4, Jetson Nano, Coral TPU, Arduino Portenta.

**Root cause:** Time constraint — the project focused on getting ESP32-S3 working. The planned RPi 4 comparison was deferred because we needed RPi hardware setup.

---

## Summary: All 16 Blockers

| # | Phase | Blocker | Fix |
|---|-------|---------|-----|
| B1 | Reference | WDT reset during AllocateTensors | `esp_task_wdt_deinit()`, 60s timeout |
| B2 | Reference | Tensor arena in SRAM (too small) | `heap_caps_malloc(..., MALLOC_CAP_SPIRAM)` |
| B3 | Reference | Model alignment crash | `__attribute__((aligned(8)))` |
| B4 | ESP-NN | esp_nn.h not found | Clone manually + `-Ilib/esp-nn/include` |
| B5 | ESP-NN | common_functions.h missing | `-Ilib/esp-nn/src/common` |
| B6 | ESP-NN | P4 RISC-V assembly on Xtensa | Delete P4 files |
| B7 | ESP-NN | Duplicate symbols (ref vs ESP-NN) | Delete ref .cc files |
| B8 | ESP-NN | Include path mismatch | Manual dir structure |
| B9 | Profiling | MicroProfiler returns 0 | Rename generic micro_time.cc |
| B10 | Logistic | Assumed wrong bottleneck | Profile first! |
| B11 | Logistic | GetScratchBuffer in Prepare | Defer LUT init to first Eval |
| B12 | Logistic | MicroProfiler 4096 overflow | Remove profiler for prod |
| B13 | Paper | PyTorch→TFLite 33pp mAP drop | Pipeline fidelity issue (unresolved) |
| B14 | Paper | No INA219 power measurement | Datasheet estimates only |
| B15 | Paper | No camera integration | Deferred |
| B16 | Paper | No comparison platform | Deferred |

---

## Results

| Configuration | Latency | FPS | Speedup |
|--------------|---------|-----|---------|
| Reference kernels | 219,287 ms | 0.0046 | 1.0× |
| ESP-NN Conv2D | 18,020 ms | 0.055 | 12.2× |
| ESP-NN + LOGISTIC LUT | **7,216 ms** | **0.139** | **30.4×** |

Remaining bottleneck: **CONV_2D** (92% of 7.2s). ESP-NN SIMD already maxed. Next: model architecture changes.

---

## Key Takeaways

1. **Profile before optimizing.** Our wrong assumption (Reshape/Concat bottleneck) would have wasted weeks. One profiling run found the real culprit: LOGISTIC (element-wise sigmoid).

2. **TFLite Micro has platform-specific traps.** The timer abstraction (`micro_time.cc` vs `esp/micro_time.cc`), the state-dependent API (`GetScratchBuffer()` only in kInvoke), and the memory planning all behave differently than desktop TFLite.

3. **ESP-NN is powerful but needs manual integration.** Not on PlatformIO registry, multi-arch bloat, include path quirks. Once set up, the SIMD Conv2D gives 12× speedup.

4. **The 30× speedup from 219s → 7.2s came from two optimization phases:** (a) SIMD Conv2D (12×), (b) LUT sigmoid (2.5×). The total is multiplicative.

5. **For journal submission:** Fix the PyTorch→TFLite accuracy gap (blocker #13, #1 priority), measure power with INA219 (#14), integrate camera (#15), and compare with RPi 4 (#16).
