import ReactFlow, { Background, ConnectionMode, Controls, Edge, EdgeChange, Node, NodeChange, SelectionMode, applyEdgeChanges, applyNodeChanges } from "reactflow";
import { Device, Topology, topologySelector } from "../redux/appSlice";
import { useAppSelector } from "../redux/hooks";

import 'reactflow/dist/style.css';
import { Box } from "@chakra-ui/react";
import { useCallback, useEffect, useState } from "react";
import DeviceNode from "./DeviceNode";

const nodeTypes = {'device': DeviceNode};

export default function TopologyGraph() {
    const topology = useAppSelector(topologySelector);

    const [nodes, setNodes] = useState(createNodes(topology, null));
    const [edges, setEdges] = useState(createEdges(topology, null));

    useEffect(() => {
        setNodes(createNodes(topology, nodes));
        setEdges(createEdges(topology, edges));

        console.log(edges)
        console.log(topology.links)

    }, [topology]);

    const onNodesChange = useCallback(
        (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
        [],
      );

      const onEdgesChange = useCallback(
        (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
        [],
      );      

    return (
        <Box w='100%' h='100%'>
            <ReactFlow 
            nodes={nodes} 
            edges={edges} 
            nodeTypes={nodeTypes} 
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            selectionMode={SelectionMode.Partial}
            connectionMode={ConnectionMode.Loose}
            nodesConnectable={false}
            deleteKeyCode={null}>
                <Background />
                <Controls />
            </ReactFlow>
        </Box>
    );
}

function createNodes(topology: Topology, oldNodes: Node<Device>[] | null): Node<Device>[] {
    return topology.devices.map((device, index) => {
        const old = oldNodes?.find((node) => node.id == device.name);
        
        if (old) {
            return {...old, data: device};
        } else {
            return {
                id: device.name,
                type: 'device',
                position: {x: index * 200, y: 100},
                data: device
            }
        }
    })
}

function createEdges(topology: Topology, oldEdges: Edge[] | null): Edge[] {
    return topology.links.map((link) => {
        const id = `${link.device1}-${link.port1}-${link.device2}-${link.port2}`;
        const old = oldEdges?.find((edge) => edge.id == id);

        if (old) {
            return old;
        } else {
            return {
                id: id,
                source: `${link.device1}`,
                sourceHandle: `${link.port1}`,
                target: `${link.device2}`,
                targetHandle: `${link.port2}`,
                type: 'straight'
            }
        }
    })
}