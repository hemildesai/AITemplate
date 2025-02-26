#  Copyright (c) Meta Platforms, Inc. and affiliates.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import logging
import unittest

import torch

from aitemplate.compiler import compile_model, ops
from aitemplate.compiler.base import IntImm
from aitemplate.frontend import Tensor
from aitemplate.testing import detect_target
from aitemplate.testing.test_utils import (
    get_random_torch_tensor,
    get_torch_empty_tensor,
)
from aitemplate.utils import shape_utils


class GEMMRcrBiasFastGeluTestCase(unittest.TestCase):
    def _test_rcr(self, Ms, test_name, use_fast_gelu=True, dtype="float16"):
        K = 1024
        N = 64
        target = detect_target()
        MDim = shape_utils.gen_int_var_min_max(Ms, name="m")
        X = Tensor(shape=[MDim, IntImm(K)], dtype=dtype, name="input_0", is_input=True)
        W = Tensor(
            shape=[IntImm(N), IntImm(K)], dtype=dtype, name="input_1", is_input=True
        )
        B = Tensor(shape=[IntImm(N)], dtype=dtype, name="input_2", is_input=True)
        OP = (
            ops.gemm_rcr_bias_fast_gelu() if use_fast_gelu else ops.gemm_rcr_bias_gelu()
        )
        Y = OP(X, W, B)
        Y._attrs["name"] = "output_0"
        Y._attrs["is_output"] = True

        module = compile_model(
            Y,
            target,
            "./tmp",
            f"gemm_rcr_bias_fast_gelu_{test_name}"
            if use_fast_gelu
            else f"gemm_rcr_bias_gelu_{test_name}",
        )

        for M in Ms:
            logging.info(f"Testing {M=}")

            X_pt = get_random_torch_tensor([M, K], dtype)
            W_pt = get_random_torch_tensor([N, K], dtype)
            B_pt = get_random_torch_tensor([N], dtype)
            Y_pt = torch.nn.GELU()(torch.nn.functional.linear(X_pt, W_pt, bias=B_pt))
            y = get_torch_empty_tensor([M, N], dtype)
            module.run_with_tensors(
                {"input_0": X_pt, "input_1": W_pt, "input_2": B_pt},
                [y],
            )
            self.assertTrue(torch.allclose(Y_pt, y, atol=1e-1, rtol=1e-1))

    def test_rcr(self):
        self._test_rcr([128], "static", use_fast_gelu=True)
        if detect_target().name() == "cuda":
            self._test_rcr([1, 7, 64, 127], "dynamic_m", use_fast_gelu=True)
            self._test_rcr([128], "static", use_fast_gelu=False)
            self._test_rcr([1, 7, 64, 127], "dynamic_m", use_fast_gelu=False)

    @unittest.skipIf(detect_target().name() == "rocm", "Not supported by ROCM.")
    @unittest.skipIf(
        detect_target().name() == "cuda" and int(detect_target()._arch) < 80,
        "Not supported by CUDA < SM80.",
    )
    def test_rcr_float(self):
        self._test_rcr(
            [1, 7, 64, 127], "fast_dynamic_m_float", use_fast_gelu=True, dtype="float"
        )
        self._test_rcr(
            [1, 7, 64, 127], "dynamic_m_float", use_fast_gelu=False, dtype="float"
        )


if __name__ == "__main__":
    unittest.main()
