import ReactFlow, { Background, ConnectionMode, Controls, Edge, Node, SelectionMode, useEdgesState, useNodesState, useOnSelectionChange } from "reactflow";
import { Device, Topology, Subnet, topologySelector, selectNodes, selectEdges, subnetsSelector, configSelector } from "../redux/appSlice";
import { useAppDispatch, useAppSelector } from "../redux/hooks";

import 'reactflow/dist/style.css';
import { Box } from "@chakra-ui/react";
import { useEffect, useMemo } from "react";
import DeviceNode from "./DeviceNode";
import SubnetNode from "./SubnetNode";
import { getLinkColor, getNetworkAddress } from "../utils";

const nodeTypes = {'device': DeviceNode, 'subnet': SubnetNode};

export default function TopologyGraph() {
    const topology = useAppSelector(topologySelector);
    const config = useAppSelector(configSelector);
    const rawSubnets = useAppSelector(subnetsSelector);
    const dispatch = useAppDispatch();

    const subnets = useMemo(
        () => {
            const subnets = [] as Subnet[];

            for (const item of rawSubnets) {
                const port = topology.devices.find((device) => device.name == item.device)?.ports[Number(item.port)];
                if (port) {
                    subnets.push({
                        device: item.device,
                        port: port.interface_name,
                        address: getNetworkAddress(item.address)
                    });
                }
            }
            
            // for (const [_, valueType] of Object.entries(config)) {
            //     for (const [keyDevice, valueDevice] of Object.entries(valueType)) {
            //         valueDevice.forEach((configLine) => {
            //             const words = configLine.split(' ');
            //             if (words[0] == 'address') {
            //                 if (topology.links.find((link) => 
            //                 (link.device1 == keyDevice && link.port1 == words[1])
            //                 || (link.device2 == keyDevice && link.port2 == words[1])) == undefined) {
            //                     subnets.push({
            //                         device: keyDevice,
            //                         port: words[1],
            //                         address: getNetworkAddress(words[2])
            //                     });
            //                 }
            //             }
            //         })
            //     }
            // }
            
            return subnets;
        },
        [rawSubnets, topology]
    )

    const linkScores = useMemo(
        () => {
            const routes = topology.devices.map(d => {
                return {device: d.name, routes: config.classic[d.name]?.filter(c => c.startsWith('route')) || 
                config.sdn[d.name]?.filter(c => c.startsWith('route')) || 0};
            });

            return topology.links.map(link => {
                const id = `${link.device1}-${link.port1}-${link.device2}-${link.port2}`;

                let score = 0;

                const device1Routes = routes.find(r => r.device == link.device1)?.routes || [];
                const device2Routes = routes.find(r => r.device == link.device2)?.routes || [];

                console.log(link.device1, device1Routes, link.device2, device2Routes)

                const device1Weight = topology.links.filter(l => l.device1 == link.device1 || l.device2 == link.device1).length;
                const device2Weight = topology.links.filter(l => l.device1 == link.device2 || l.device2 == link.device2).length;

                score += device1Routes.filter(r => 
                    (r.includes('route ') && r.includes(` ${link.port1} `))
                || (r.includes('route-f') && r.endsWith(link.port1)))
                .length * device1Weight / device1Routes.length;
                score += device2Routes.filter(r => 
                    (r.includes('route ') && r.includes(` ${link.port2} `))
                || (r.includes('route-f') && r.endsWith(link.port2))
                ).length * device2Weight / device2Routes.length;
        
                return {id: id, score: score * 10}
            });
        },
        [topology, config]
    )

    const [nodes, setNodes, onNodesChange] = useNodesState(createNodes(topology, subnets, null));
    const [edges, setEdges, onEdgesChange] = useEdgesState(createEdges(topology, subnets, linkScores, null));

    useEffect(() => {
        setNodes(createNodes(topology, subnets, nodes));
        setEdges(createEdges(topology, subnets, linkScores, edges));
    }, [subnets, topology, linkScores]); 

    useOnSelectionChange({
        onChange: ({ nodes, edges }) => {
            dispatch(selectNodes(nodes));
            dispatch(selectEdges(edges));
        },
    })

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

function createEdges(topology: Topology, subnets: Subnet[], scores: {id: string, score: number}[], oldEdges: Edge[] | null): Edge[] {
    const devices = topology.links.map((link) => {
        const id = `${link.device1}-${link.port1}-${link.device2}-${link.port2}`;
        const old = oldEdges?.find((edge) => edge.id == id);
        const score = scores.find(s => s.id == id)?.score;

        const maxScore = 50;
        const minScore = Math.min(...scores.map(s => s.score));

        const style = {
            stroke: score ? getLinkColor((score - minScore) / (maxScore - minScore)) : 'gray',
            strokeWidth: score ? 4 : 2
        }

        if (old) {
            return {...old, style, 
                // label: score
            };
        } else {
            return {
                id: id,
                source: `${link.device1}`,
                sourceHandle: `${link.port1}`,
                target: `${link.device2}`,
                targetHandle: `${link.port2}`,
                type: 'straight',
                // label: score,
                style
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
                type: 'straight',
                animated: true
            }
        }
    });

    return [...devices, ...subnetsEdges];
}