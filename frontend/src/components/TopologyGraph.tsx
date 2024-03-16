import ReactFlow, { Background, ConnectionMode, Controls, Edge, Node, SelectionMode, useEdgesState, useNodesState } from "reactflow";
import { Device, Topology, Subnet, configSelector, topologySelector } from "../redux/appSlice";
import { useAppSelector } from "../redux/hooks";

import 'reactflow/dist/style.css';
import { Box } from "@chakra-ui/react";
import { useEffect, useMemo } from "react";
import DeviceNode from "./DeviceNode";
import SubnetNode from "./SubnetNode";
import { getNetworkAddress } from "../utils";

const nodeTypes = {'device': DeviceNode, 'subnet': SubnetNode};

export default function TopologyGraph() {
    const topology = useAppSelector(topologySelector);
    const config = useAppSelector(configSelector);

    const subnets = useMemo(
        () => {
            const subnets = [] as Subnet[];
            
            for (const [_, valueType] of Object.entries(config)) {
                for (const [keyDevice, valueDevice] of Object.entries(valueType)) {
                    valueDevice.forEach((configLine) => {
                        const words = configLine.split(' ');
                        if (words[0] == 'address') {
                            if (topology.links.find((link) => 
                            (link.device1 == keyDevice && link.port1 == words[1])
                            || (link.device2 == keyDevice && link.port2 == words[1])) == undefined) {
                                subnets.push({
                                    device: keyDevice,
                                    port: words[1],
                                    address: getNetworkAddress(words[2])
                                });
                            }
                        }
                    })
                }
            }

            return subnets;
        },
        [config]
    )

    const [nodes, setNodes, onNodesChange] = useNodesState(createNodes(topology, subnets, null));
    const [edges, setEdges, onEdgesChange] = useEdgesState(createEdges(topology, subnets, null));

    useEffect(() => {
        setNodes(createNodes(topology, subnets, nodes));
        setEdges(createEdges(topology, subnets, edges));

        console.log(edges)
        console.log(topology.links)

    }, [topology]); 

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
            deleteKeyCode={null}
            fitView>
                <Background />
                <Controls />
            </ReactFlow>
        </Box>
    );
}

// TODO: temporary solution
function getInitialPosition(topology: Topology, name: string, counter: number): {x: number, y: number} {
    // const device = topology.devices.find((device) => device.name == name)!;
    const links = topology.links.filter((link) => link.device1 == name || link.device2 == name).length;
    const y = 1000 - links * 100;
    return {x: counter * 200, y};
}

function createNodes(topology: Topology, subnets: Subnet[], oldNodes: Node<Device | Subnet>[] | null): Node<Device | Subnet>[] {
    let counter = 0;

    const devices = topology.devices.map((device, _) => {
        const old = oldNodes?.find((node) => node.id == device.name);
        
        if (old) {
            return {...old, data: device};
        } else {
            return {
                id: device.name,
                type: 'device',
                position: getInitialPosition(topology, device.name, counter++),
                data: device
            }
        }
    });

    const subnetsNodes = subnets.map((subnet, _) => {
        const old = oldNodes?.find((node) => node.id == `SUBNET-${subnet.device}-${subnet.port}`);

        if (old) {
            return {...old, data: subnet};
        } else {
            const devicePosition = devices.find((device) => device.id == subnet.device)?.position || {x: 100, y: 100}

            return {
                id: `SUBNET-${subnet.device}-${subnet.port}`,
                type: 'subnet',
                position: {x: devicePosition.x - 20, y: devicePosition.y + 120},
                data: subnet
            }
        }
    });

    return [...devices, ...subnetsNodes];
}

function createEdges(topology: Topology, subnets: Subnet[], oldEdges: Edge[] | null): Edge[] {
    const devices = topology.links.map((link) => {
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

    const subnetsEdges = subnets.map((subnet) => {
        const id = `SUBNET-EDGE-${subnet.device}-${subnet.port}`;
        const old = oldEdges?.find((edge) => edge.id == id);

        if (old) {
            return old;
        } else {
            return {
                id: id,
                source: `${subnet.device}`,
                sourceHandle: `${subnet.port}`,
                target: `SUBNET-${subnet.device}-${subnet.port}`,
                targetHandle: 'SUBNET-HANDLE',
                type: 'straight'
            }
        }
    });

    return [...devices, ...subnetsEdges];
}