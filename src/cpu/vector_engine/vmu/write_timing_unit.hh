/*
 * Copyright (c) 2020 Barcelona Supercomputing Center
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * Author: Cristóbal Ramírez
 */

#ifndef __CPU_MEM_UNIT_WRITE_TIMING__
#define __CPU_MEM_UNIT_WRITE_TIMING__

#include <cstdint>
#include <deque>
#include <functional>

#include "arch/riscv/insts/vector_static_inst.hh"
#include "base/statistics.hh"
#include "cpu/minor/exec_context.hh"
#include "cpu/vector_engine/vector_engine.hh"
#include "params/MemUnitWriteTiming.hh"
#include "sim/ticked_object.hh"
#include "cpu/vector_engine/defines.hh"

class VectorEngine;
//class ExecContextPtr;
//class ExecContext;

class MemUnitWriteTiming : public TickedObject
{
public:
    MemUnitWriteTiming(const MemUnitWriteTimingParams &p);
    ~MemUnitWriteTiming();

    // overrides
    void evaluate() override;
    void regStats() override;

    void queueData(uint8_t *data);
    void queueAddrs(uint8_t *data);
    void initialize(VectorEngine& vector_wrapper, uint64_t count,
        uint64_t DST_SIZE,uint64_t mem_addr,uint8_t mop,uint64_t stride,
        Location data_to,ExecContextPtr& xc,
        std::function<void(bool)> on_item_store);

private:
    //set by params
    const uint8_t channel;
    const uint64_t cacheLineSize;
    const uint64_t VRF_LineSize;

    volatile bool done;
    std::deque<uint8_t *> dataQ;
    //Used by indexed Operations to hold the element index
    std::deque<uint8_t *> AddrsQ;
    std::function<bool(void)> writeFunction;

    //modified by writeFunction closure over time
    uint64_t vecIndex;
    VectorEngine* vectorwrapper;

public:
    // Stat for number of cache lines write requested
    Stats::Scalar Cache_line_w_req;
};

#endif //__CPU_MEM_UNIT_WRITE_TIMING__
