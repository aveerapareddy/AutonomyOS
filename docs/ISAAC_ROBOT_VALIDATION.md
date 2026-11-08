# Isaac Sim robot and RTX camera validation

A real rented RTX 6000 Ada run validated an official Jetbot asset in the exported transfer-lane USD stage using Isaac Sim **6.2.0.0**, NVIDIA driver **595.91.07** and the RayTracedLighting renderer. This advances the earlier import-only smoke to one bounded closed-loop robot case and actual RTX RGB output.

| Check | Measured result |
|---|---|
| Controller | Bounded differential drive, goal at (0, 6) m |
| Controller steps | 2,489, limit 4,200 |
| Physics timestep | 1/60 second |
| Final planar goal error | 0.3966841472 m, required less than 0.5 m |
| Initial and final sensor frames | Two decoded nonblank 320 × 240 RGBA PNGs |
| Frame integrity | Independent SHA-256 and PNG-dimension checks passed locally |
| Input stage | `999f2137c899983795ee0d25bbb43c363f7a37d691c2e551efe2332e68b1008b` |
| Final robot/camera source | `acf8534` |
| CPU deployment source in the same bundle | `5c172a5`, 176 tests plus HTTP/restart gates |
| Complete archive | 66 files, 1,857,328 bytes |
| Complete archive SHA-256 | `1cac82419df73274635513b0a17d5366c24603d75fdea94b9cf4cf39aec2a427` |

The complete archive and separate source snapshots were copied locally, independently verified, and images decoded before pod `klmeroyw7p9kvu` was stopped. Provider details then showed compute/storage not running and total $0.00/hour. The externally verified HTTPS demo was temporary and is no longer claimed to be live.

## Failures retained and fixes

The first install rejected the CPU vision environment's Pillow 13 pin because Isaac requires Pillow below 13. The Isaac environment now pins 12.1.1 separately. That initial install log was overwritten by its retry; the controller failure and explicit attempt history are retained. Do not describe the first log as fully recovered.

Three camera attempts failed, including an incorrect annotator method name and a Vulkan initialization failure. A zero process exit did **not** mean success: the simulator shutdown path could exit zero after a failed report. The independent artifact validator now rejects a false report regardless of exit status, checks actual goal geometry and motion, and verifies input/frame hashes and bounds. Regression tests preserve this failure mode.

CUDA recognized the GPU while Vulkan failed. The image already exposed NVIDIA driver libraries, but lacked GL dispatch and other graphics dependencies. Installing official Ubuntu packages including `libegl1`, `libgl1`, `libglx0` and the documented X11 libraries made `vulkaninfo --summary` identify the actual RTX device. The reproducible prerequisite script performs that preflight without installing a kernel driver.

The first passing camera was narrowly framed. Additional camera runs and their reports are retained; the final focal setting frames the lane. They reproduce the same measured goal outcome but are not independent varied navigation scenarios.

## Reproduce and interpret

Accept the Omniverse terms through your own authorized workflow first. In a disposable supported Ubuntu GPU container, set graphics capabilities at creation, run `bash scripts/isaac_system_dependencies.sh`, and retain the Vulkan result. Use `python -m scripts.cloud_cpu_demo --help`, followed by `scripts.cloud_isaac_robot --help`, to create separate CPU and Isaac environments and run bounded checks. The caller must supply explicit EULA approval; the scripts do not infer it from a failed run.

The camera annotator/warm-up behavior follows the [official Isaac camera API](https://docs.isaacsim.omniverse.nvidia.com/6.2.0/py/source/deprecated/isaacsim.sensors.camera/docs/api.html). A valid image is not a perception-accuracy result. The test uses default World physics configuration and does not explicitly enable GPU dynamics. It is not a general navigation benchmark, obstacle-avoidance study, learned-control result or physical-safety certification. All controller and camera evidence is scoped to this one synthetic lane.
