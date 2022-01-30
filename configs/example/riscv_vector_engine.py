# Copyright (c) 2020 Barcelona Supercomputing Center
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Author: Cristobal Ramirez

import sys
import math
import datetime

import m5
from m5.objects import *
from m5.util import addToPath, fatal
from optparse import OptionParser

addToPath('../')

from common import Options
from common import Simulation
from common import CacheConfig
from common import CpuConfig
from common import MemConfig
from common.Caches import *


# Parse options
ps = OptionParser()

# General Options
ps.add_option('--cmd',              type="string",
                                    help="Command to run on the CPU")
ps.add_option('--output',           type="string",
                                    help="Outputs")
ps.add_option('--options',          type="string",
                                    help="Options")
ps.add_option('--cache_line_size',  type="int", default=64,
                                    help="System Cache Line Size in Bytes")
ps.add_option('--l1i_size',         type="string", default='32kB',
                                    help="L1 instruction cache size")
ps.add_option('--l1d_size',         type="string", default='32kB',
                                    help="L1 data cache size")
ps.add_option('--l2_size',          type="string", default='256kB',
                                    help="Unified L2 cache size")
ps.add_option('--mem_size',         type="string", default='2048MB',
                                    help="Size of the DRAM")
ps.add_option('--cpu_clk',          type="string", default='2GHz',
                                    help="Speed of all CPUs")

# Vector Register Options
ps.add_option('--renamed_regs',     type="int", default=40,
                                    help="Number of Vector Physical Registers")
ps.add_option('--VRF_line_size',    type="int", default=8,
                                    help="Vector Register Slice line size in Bytes (per lane)")
# Vector Queues Options
ps.add_option('--OoO_queues',       type="int", default=False,
                                    help="Out-of-Order/In-Order Queues")
ps.add_option('--mem_queue_size',   type="int", default=32,
                                    help="Memory Queues")
ps.add_option('--arith_queue_size', type="int", default=32,
                                    help="Vector Arithmetic")
# REORDER BUFFER OPTIONS
ps.add_option('--rob_size',         type="int", default=64,
                                    help="Reorder Buffer size")

# Vector Exec Unit Options
ps.add_option('--vector_clk',       type="string", default='1GHz',
                                    help="Speed of Vector Accelerator")
ps.add_option('--v_lanes',          type="int", default=8,
                                    help="Number of Lanes")
ps.add_option('--max_vl',           type="int", default=16384,
                                    help="Maximum Vector Length in bits")
ps.add_option('--num_clusters',     type="int", default=1,
                                    help="Number execution clusters")

ps.add_option('--connect_to_l1_d',  type="int", default=False,
                                    help="Connect Vector Port to L1D")
ps.add_option('--connect_to_l1_v',  type="int", default=False,
                                    help="Connect Vector Port to L1V")
ps.add_option('--connect_to_l2',    type="int", default=True,
                                    help="Connect Vector Port to L2")
ps.add_option('--connect_to_dram',  type="int", default=False,
                                    help="Connect Vector Port to Dram")

(options, args) = ps.parse_args()

###############################################################################
# Memory hierarchy configuration
# Here you can select where to connect the vector memory port, it can be;
# to main memory
# to l2 cache
# to l1 data cache (share with the core)
# to its own vector cache
###############################################################################

connect_to_dram   = options.connect_to_dram
connect_to_l2     = options.connect_to_l2
connect_to_l1d    = options.connect_to_l1_d
connect_to_l1V    = options.connect_to_l1_v

multi_port = True
vector_rf_ports = (((options.num_clusters*5)+3) if multi_port else 1)

###############################################################################
# Setup System
###############################################################################

# Create the system we are going to simulate
system = System(
    cache_line_size = options.cache_line_size,
    clk_domain = SrcClockDomain(
        clock = options.cpu_clk,
        voltage_domain = VoltageDomain()
    ),
    mem_mode = 'timing',
    mem_ranges = [AddrRange(options.mem_size)]
)

###############################################################################
# CPU Config
###############################################################################
system.cpu = MinorCPU()

# Create CPU and add simple ICache and DCache

system.cpu.icache = Cache(
    size = options.l1i_size,
    assoc = 4,
    tag_latency = 4,
    data_latency = 4,
    response_latency = 4,
    mshrs = 4,
    tgts_per_mshr = 20
)

system.cpu.dcache = Cache(
    size = options.l1d_size,
    assoc = 4,
    tag_latency = 4,
    data_latency = 4,
    response_latency = 4,
    mshrs = 4,
    tgts_per_mshr = 20
)

# Setup vector cache
if (not connect_to_l1d) and (not connect_to_l2) and (not connect_to_dram):
    system.VectorCache = Cache(
        size = options.l1d_size,
        assoc = 4,
        tag_latency = 4,
        data_latency = 4,
        response_latency = 4,
        mshrs = 4,
        tgts_per_mshr = 20
    )

if connect_to_l2 or connect_to_dram:
    system.VectorCache = Cache(
        size = "2kB",
        assoc = 1,
        tag_latency = 0,
        data_latency = 0,
        response_latency = 0,
        mshrs = 4,
        tgts_per_mshr = 20
    )

###############################################################################
# Vector extension config
###############################################################################

system.cpu.ve_interface = VectorEngineInterface(
    vector_engine = VectorEngine(
        vector_rf_ports = vector_rf_ports,
        vector_config = VectorConfig(
            max_vl = options.max_vl
        ),
        vector_reg = VectorRegister(
            num_lanes = options.v_lanes/options.num_clusters,
            num_regs = options.renamed_regs,
            mvl = options.max_vl,
            size = (options.renamed_regs * options.max_vl)/8,
            lineSize =options.VRF_line_size
                        *(options.v_lanes/options.num_clusters),
            numPorts = vector_rf_ports,
            accessLatency = 1
        ),
        vector_inst_queue = InstQueue(
            OoO_queues=options.OoO_queues,
            vector_mem_queue_size = options.mem_queue_size,
            vector_arith_queue_size = options.arith_queue_size
        ),
        vector_rename = VectorRename(
            PhysicalRegs = options.renamed_regs
        ),
        vector_rob = ReorderBuffer(
            ROB_Size = options.rob_size
        ),
        vector_reg_validbit = VectorValidBit(
            PhysicalRegs = options.renamed_regs
        ),
        vector_memory_unit = VectorMemUnit(
            memReader = MemUnitReadTiming(
                channel = (((options.num_clusters-1)*5)+5
                           if multi_port else 0),
                cacheLineSize = options.cache_line_size,
                VRF_LineSize = options.VRF_line_size
                               * (options.v_lanes/options.num_clusters)
            ),
            memWriter = MemUnitWriteTiming(
                channel = (((options.num_clusters-1)*5)+6
                           if multi_port else 0),
                cacheLineSize = options.cache_line_size,
                VRF_LineSize = options.VRF_line_size
                               * (options.v_lanes/options.num_clusters)
            ),
            memReader_addr = MemUnitReadTiming(
                channel = (((options.num_clusters-1)*5)+7
                           if multi_port else 0),
                cacheLineSize = options.cache_line_size,
                VRF_LineSize = options.VRF_line_size
                               * (options.v_lanes/options.num_clusters)
            )
        ),
        num_clusters = options.num_clusters,
        num_lanes = options.v_lanes,
        vector_lane = [VectorLane(
            lane_id = lane_id,
            srcAReader = MemUnitReadTiming(
                channel = ((lane_id*5)+0 if multi_port else 0),
                cacheLineSize = options.cache_line_size,
                VRF_LineSize =  options.VRF_line_size
                                * (options.v_lanes/options.num_clusters)
            ),
            srcBReader = MemUnitReadTiming(
                channel = ((lane_id*5)+1 if multi_port else 0),
                cacheLineSize = options.cache_line_size,
                VRF_LineSize = options.VRF_line_size
                        * (options.v_lanes/options.num_clusters)
            ),
            srcMReader = MemUnitReadTiming(
                channel = ((lane_id*5)+2 if multi_port else 0),
                cacheLineSize = options.cache_line_size,
                VRF_LineSize =  options.VRF_line_size
                                * (options.v_lanes/options.num_clusters)
            ),
            dstReader = MemUnitReadTiming(
                channel = ((lane_id*5)+3 if multi_port else 0),
                cacheLineSize = options.cache_line_size,
                VRF_LineSize =  options.VRF_line_size
                                * (options.v_lanes/options.num_clusters)
            ),
            dstWriter = MemUnitWriteTiming(
                channel = ((lane_id*5)+4 if multi_port else 0),
                cacheLineSize = options.cache_line_size,
                VRF_LineSize =  options.VRF_line_size
                                * (options.v_lanes/options.num_clusters)
            ),
            dataPath = Datapath(
                VectorLanes = (options.v_lanes/options.num_clusters),
                clk_domain = SrcClockDomain(
                    clock = options.vector_clk,
                    voltage_domain = VoltageDomain()
                )
            )
        ) for lane_id in range(0, options.num_clusters)]
    )
)

###############################################################################
# Create l1Xbar
###############################################################################

if connect_to_l1d:
    system.l1bus = CoherentXBar(
        forward_latency = 0,
        frontend_latency = 0,
        response_latency = 0,
        snoop_response_latency = 0,
        width = options.cache_line_size
    )

###############################################################################
# Create l2Xbar and SystemXBar
###############################################################################

system.l2bus = L2XBar()
system.membus = SystemXBar()

###############################################################################
# Connect CPU Ports and Vector Port
###############################################################################

def connect_cpu_ports1(cpu, vector_engine, l1bus, l2bus):
    cpu.icache.mem_side = l2bus.cpu_side_ports
    cpu.dcache.mem_side = l2bus.cpu_side_ports
    cpu.icache_port = cpu.icache.cpu_side
    cpu.dcache_port = l1bus.cpu_side_ports

    vector_engine.vector_mem_port = l1bus.cpu_side_ports
    l1bus.mem_side_ports = cpu.dcache.cpu_side

    # Connect vector_reg ports for each mem_unit
    for _ in range(0, vector_rf_ports):
        vector_engine.vector_reg_port = vector_engine.vector_reg.port

def connect_cpu_ports2(cpu,vector_engine,l2bus,membus):
    cpu.icache.mem_side = l2bus.cpu_side_ports
    cpu.dcache.mem_side = l2bus.cpu_side_ports
    cpu.icache_port = cpu.icache.cpu_side
    cpu.dcache_port = cpu.dcache.cpu_side

    vector_engine.vector_mem_port = system.VectorCache.cpu_side
    if connect_to_l1V:
        system.VectorCache.mem_side = l2bus.cpu_side_ports
    elif connect_to_l2:
        system.VectorCache.mem_side = l2bus.cpu_side_ports
    elif connect_to_dram:
        system.VectorCache.mem_side = membus.cpu_side_ports

    for _ in range(0, vector_rf_ports):
        vector_engine.vector_reg_port = vector_engine.vector_reg.port

if connect_to_l1d:
    connect_cpu_ports1(system.cpu, system.cpu.ve_interface.vector_engine,
                       system.l1bus, system.l2bus)
else:
    connect_cpu_ports2(system.cpu, system.cpu.ve_interface.vector_engine,
                       system.l2bus, system.membus)

###############################################################################
# Everything from the l2Xbar down
###############################################################################

# Create an L2 cache and connect it to the l2bus and systemBus
system.l2cache = Cache(
    size = options.l2_size,
    assoc = 8,
    tag_latency = 12,
    data_latency = 12,
    response_latency = 12,
    mshrs = 20,
    tgts_per_mshr = 12
)

system.l2cache.mem_side = system.membus.cpu_side_ports
system.l2cache.cpu_side = system.l2bus.mem_side_ports

# Create interrupt controller
system.cpu.createInterruptController()

# Connect the system up to the membus
system.system_port = system.membus.cpu_side_ports

# Create a DDR3 memory controller
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8(device_size = options.mem_size)
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

###############################################################################
# Create Workload
###############################################################################

process = Process()

filtered = []

if not options or not options.cmd:
    print("No --cmd='<workload> [args...]' passed in")
    sys.exit(1)
else:
    split = options.cmd.split(' ')
    for s in options.cmd.split(' '):
      if len(s):
        filtered = filtered + [s]


    process.executable = filtered[0]
    system.workload = SEWorkload.init_compatible(process.executable)
    process.cmd = filtered

system.cpu.workload = process
system.cpu.createThreads()


###############################################################################
# Run Simulation
###############################################################################

# Setup the root SimObject and start the simulation
root = Root(full_system = False, system = system)

# Instantiate all of the objects we've created above
m5.instantiate()

print("Beginning simulation!")
exit_event = m5.simulate()
print('Exiting @ tick %i because %s' % (m5.curTick(), exit_event.getCause()))
print("gem5 finished %s" % datetime.datetime.now().strftime("%b %e %Y %X"))
