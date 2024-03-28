import { Handle, NodeProps, NodeToolbar, Position } from "reactflow";
import { Device, deleteDevice, openDevice } from "../redux/appSlice";
import { Box, Center, IconButton } from "@chakra-ui/react";
import RouterIcon from "./RouterIcon";
import { DeleteIcon, EditIcon } from "@chakra-ui/icons";
import { useAppDispatch } from "../redux/hooks";

export default function DeviceNode(props: NodeProps<Device>) {
    const bg = props.data.type == 'Classic' ? 'bg.classic' : 'bg.sdn'
    const border = props.data.type == 'Classic' ? 'border.classic' : 'border.sdn'
    
    const dispatch = useAppDispatch();

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
                        <Handle key={props.data.name+port.interface_name} type='source' position={Position.Top} id={port.interface_name}
                        style={{left: '40px', top: '37px', visibility: 'hidden'}} />
                    )
                })
            }
            <Box textAlign='center' fontWeight='bold'>
                {props.data.name}
            </Box>
            <NodeToolbar position={Position.Top}>
                <IconButton aria-label="edit" size='sm' icon={<EditIcon />} marginX='5px'
                onClick={() => {dispatch(openDevice({
                    mode: 'edit',
                    editOriginal: props.data
                }))}} />
                {
                    props.data.type == 'Classic' ?
                    <IconButton aria-label="delete" size='sm' icon={<DeleteIcon />}
                    onClick={() => {dispatch(deleteDevice(props.data))}}/>
                    : <></>
                }
            </NodeToolbar>
        </Box>
    )
}