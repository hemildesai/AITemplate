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
"""
GEMM Specialization for A[RowMajor], B[ColMajor], C[RowMajor]
This is special in template based gemm solution
This is used for `torch.nn.functional.linear`
When use for `linear`, need set A->Data, B->Weight
"""
import jinja2

from ... import registry
from ..gemm_universal import common
from . import common_softmax, gemm_rcr_softmax


# pylint: disable=C0103,C0415,W0613,C0301,R1705,R1703


PROBLEM_ARGS_TEMPLATE = jinja2.Template(
    """
    /*
        A: M*K (RowMajor)
        B: N*K (ColumnMajor)
        C/D/sofmax: M*N (RowMajor)
        N: M*1 (RowMajor)
    */

    {M, N, K},               // cutlass::gemm::GemmCoord problem_size
    1,                       // int32_t batch_count_
    {a_ptr, LayoutA(K)},     // TensorRefA ref_A_
    {b_ptr, LayoutB(K)},     // TensorRefB ref_B_
    {c_ptr, 0},              // TensorRefC ref_C_
    {d_ptr, LayoutC(N)},     // TensorRefC ref_D_
    {
        float(1.0),
        float(1.0)
    },                       // typename EpilogueFunctorOp::Params linear_scaling
    {n_ptr, LayoutC(1)},     // ???
    {soft_ptr, LayoutC(N)},  // ???
"""
)


@registry.reg("cuda.gemm_rcr_bias_softmax.config")
def gemm_rcr_bias_softmax_config(func_attrs, dtype="float16"):
    return gemm_rcr_softmax.gemm_rcr_softmax_config(func_attrs, dtype)


@registry.reg("cuda.gemm_rcr_bias_softmax.gen_profiler")
def gen_profiler(func_attrs, workdir, dim_info_dict):
    return gemm_rcr_softmax.common_gen_profiler(
        func_attrs,
        workdir,
        dim_info_dict,
        common_softmax.SRC_TEMPLATE,
        PROBLEM_ARGS_TEMPLATE,
    )


@registry.reg("cuda.gemm_rcr_bias_softmax.gen_function")
def gen_function(
    func_attrs,
    exec_cond_template,
    dim_info_dict,
):
    return gemm_rcr_softmax.gen_function(
        func_attrs,
        exec_cond_template,
        dim_info_dict,
        PROBLEM_ARGS_TEMPLATE,
    )


@registry.reg("cuda.gemm_rcr_bias_softmax.func_decl")
def gen_function_decl(func_attrs):
    return gemm_rcr_softmax.gen_function_decl(func_attrs)


@registry.reg("cuda.gemm_rcr_bias_softmax.func_call")
def gen_function_call(func_attrs, indent="  "):
    return gemm_rcr_softmax.gen_function_call(
        func_attrs,
        indent,
    )


@registry.reg("cuda.gemm_rcr_bias_softmax.filter")
def function_filter(cfg, func_attrs, ab_alignment):
    """Generates function filter.

    Parameters
    ----------
    cfg: str
        The filename generated for profiler.
    func_attrs : Dict
        Stores the operation attributes.
    ab_alignment:
        Input alignments.

    Returns
    -------
    bool
        If input cfg should be filtered.
    """
    return common.function_filter(cfg, func_attrs, ab_alignment)
