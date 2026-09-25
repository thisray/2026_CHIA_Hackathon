# Notices

Project-authored code, documentation, and result records are distributed under the [MIT License](LICENSE). Included or derived upstream material remains subject to its own license.

## CHIA

The runtime uses [CHIA](https://github.com/ucb-bar/chia) at revision `16c35e92aaaf9511c6453bf94cd5cf589698f4e3`. CHIA is not bundled. Its [BSD 3-Clause license](https://github.com/ucb-bar/chia/blob/16c35e92aaaf9511c6453bf94cd5cf589698f4e3/LICENSE) names The Regents of the University of California.

## Common Cells

The ECC design derives from [Common Cells](https://github.com/pulp-platform/common_cells) at revision `121182eaa0fa1f67b74eaa97c73b8a7133adda6a`. Its pinned license is included at [LICENSES/common_cells_LICENSE.txt](LICENSES/common_cells_LICENSE.txt). Upstream-derived portions of generated artifacts retain the applicable Common Cells terms. The source and replay archives do not include the Common Cells RTL source tree.

The following notices are preserved from the pinned upstream sources:

```text
cc_ecc_decode.sv:
// Copyright 2020 ETH Zurich and University of Bologna.
// Copyright and related rights are licensed under the Solderpad Hardware
// License, Version 0.51 (the "License"); you may not use this file except in
// compliance with the License. You may obtain a copy of the License at
// http://solderpad.org/licenses/SHL-0.51. Unless required by applicable law
// or agreed to in writing, software, hardware and materials distributed under
// this License are distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
// CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.
// Author: Florian Zaruba <zarubaf@iis.ee.ethz.ch>

cc_pkg.sv:
// Copyright 2025 ETH Zurich and University of Bologna.
// Solderpad Hardware License, Version 0.51, see LICENSE for details.
// SPDX-License-Identifier: SHL-0.51
```

## Tool and platform data

The pinned IIC-OSIC image supplies the Sky130A PDK/library files used at execution time. The image and raw PDK files are not bundled in this repository. The replay archive contains generated netlists, ODB and SPEF files, logs, VCDs, and execution records; these may reference upstream cell names or contain derived circuit material.
