# RescueVision Edge — ESP-NN Logistic Optimization

## Problem
ESP-NN enabled Conv2D SIMD optimizations gave a 12.2× speedup (219s → 18s), but inference was still too slow. We needed to identify and fix the remaining bottleneck.

## Approach
1. **Profile first** — Integrated TFLite Micro's `MicroProfiler` with ESP timer (`esp_timer_get_time()`) to get per-op latency breakdown
2. **Identify bottleneck** — LOGISTIC (sigmoid) consumed 62.3% of inference time (11,758 ms), Conv2D was 35.2% (6,634 ms)
3. **ESP-NN logistic API** — ESP-NN v1.2.3 already had `esp_nn_logistic_s8()` with LUT-based sigmoid (256-byte table, O(1) per element)
4. **Implement wrapper** — Created `esp_nn/logistic.cc` following the pattern of existing `esp_nn/` wrappers

## Blockers Encountered

### B1: Duplicate Symbols
Deleting reference `logistic.cc` was needed to avoid multiple `Register_LOGISTIC()` definitions. Same pattern as conv/depthwise_conv/fully_connected.

### B2: `GetScratchBuffer()` in Prepare Phase
```
TFLITE_DCHECK(state_ == InterpreterState::kInvoke);
```
The LUT preparation (`esp_nn_logistic_s8_prepare`) calls `GetScratchBuffer()` which only works during `kInvoke`. During `Prepare`, state is `kPrepare`. Fix: defer LUT preparation to the first `Eval` call using a `lut_prepared` flag in `NodeData`.

### B3: MicroProfiler Event Overflow
After 16 inferences, MicroProfiler hit the 4096-event limit and crashed. The profiler counts every op invocation across all inferences as separate events.

## Process
1. Enabled ESP-NN (Conv2D, depthwise, etc.) — 12.2× speedup
2. Profiled with MicroProfiler — identified LOGISTIC at 62.3%
3. Wrote `esp_nn/logistic.cc` with LUT-based sigmoid
4. Removed reference `logistic.cc` to avoid duplicate symbols
5. Built and deployed — crashed on `GetScratchBuffer` during Prepare
6. Fixed by deferring LUT init to first Eval call
7. Rebuilt and benchmarked

## Result
| Metric | Before (ESP-NN) | After (+Logistic) | Speedup |
|--------|:-:|:-:|:-:|
| Avg inference | 18,020 ms | **7,216 ms** | **2.5×** |
| Min / Max | 18,006 / 18,042 ms | 7,214 / 7,237 ms | |
| FPS | 0.055 | **0.139** | |
| PSRAM | 3.93 MB | 3.93 MB (stable) | |
| Inferences in 120s | 6 | **16** | |

Combined speedup from reference kernels (219,287 ms): **30.4×**.

Remaining bottleneck: **CONV_2D** (~6.6s or ~92% of total). ESP-NN conv is already SIMD-optimized. Further gains require model architecture changes (shallower backbone, smaller input).
