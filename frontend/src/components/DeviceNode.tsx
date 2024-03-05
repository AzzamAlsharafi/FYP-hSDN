import { Handle, NodeProps, Position } from "reactflow";
import { Device } from "../redux/appSlice";
import { Box, Center } from "@chakra-ui/react";
import RouterIcon from "./RouterIcon";

export default function DeviceNode(props: NodeProps<Device>) {
    const bg = props.data.type == 'Classic' ? 'bg.classic' : 'bg.sdn'
    const border = props.data.type == 'Classic' ? 'border.classic' : 'border.sdn'

    return (
        <Box>
            <Center borderRadius='50' boxSize='80px'
                border={props.selected ? '4px' : '2px'}
                borderColor={props.selected ? 'black' : border}
                bg={props.selected ? border : bg}
                _hover={{ bg: border }}
            >
                <RouterIcon boxSize='80px'
                    color={props.selected ? bg : border}
                    _hover={{ color: bg }} />
            </Center>
            {
                props.data.ports.map((port) => {
                    return (
                        <Handle type='source' position={Position.Top} id={port.interface_name}
                        style={{left: '40px', top: '37px', visibility: 'hidden'}} />
                    )
                })
            }
            <Box textAlign='center' fontWeight='bold'>
                {props.data.name}
            </Box>
        </Box>
    )
}