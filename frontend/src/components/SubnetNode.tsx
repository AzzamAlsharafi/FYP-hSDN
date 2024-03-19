import { Handle, NodeProps, Position } from "reactflow";
import { Subnet } from "../redux/appSlice";
import { Box, Center } from "@chakra-ui/react";

export default function SubnetNode(props: NodeProps<Subnet>) {
    const bg = 'green.200'
    const border = 'darkgreen'

    return (
        <Box>
            <Center w='120px' h='40px'
                border={props.selected ? '4px' : '2px'}
                borderColor={props.selected ? 'black' : border}
                bg={props.selected ? border : bg}
                textColor={props.selected ? bg : border}
                _hover={{ bg: border, textColor: bg }}
            >
                <Box textAlign='center' fontWeight='bold' >
                    {props.data.address}
                </Box>
            </Center>
            <Handle type='source' position={Position.Top} id={'SUBNET-HANDLE'}
                        style={{left: '60px', top: '17px', visibility: 'hidden'}} />
            
        </Box>
    )
}