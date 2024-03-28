import { Box, Button, Divider, Flex, Text } from "@chakra-ui/react";
import { useAppDispatch, useAppSelector } from "../redux/hooks";
import { nodesSelector, openDevice, openPolicy } from "../redux/appSlice";
import SummaryPanel from "./SummaryPanel";
import NodePanel from "./NodePanel";
import PolicyModal from "./PolicyModal";
import PoliciesList from "./PoliciesList";
import DeviceModal from "./DeviceModal";

export default function Panel() {
    const selectedNodes = useAppSelector(nodesSelector);
    const dispatch = useAppDispatch();

    return <>
        <Box bg='lightgrey' borderRadius='20px' minW='400px' padding='10px'>
            <Box bg='white' borderRadius='20px' padding='20px'>
                {selectedNodes.length == 0 ? <SummaryPanel /> 
                : selectedNodes.length == 1 ? <NodePanel node={selectedNodes[0]} /> 
                : <Text>MANY</Text>}

                
                <Divider/>
                <Divider/>
                <Divider/>
                <Divider/>
                                
                <Box marginY='10px' maxH='300px' overflowY='auto'
                css={{
                    '&::-webkit-scrollbar': {
                      width: '4px',
                    },
                    '&::-webkit-scrollbar-thumb': {
                      background: 'grey',
                      borderRadius: '24px',
                    },
                  }}
                >
                    <PoliciesList/>
                </Box>

                <Divider/>
                <Divider/>
                <Divider/>
                <Divider/>

                <Flex paddingTop='20px'>
                    <Button flex='1' marginLeft='5px'
                    onClick={() => {dispatch(openPolicy({mode: 'create'}))}} >New Policy</Button>
                    <Button flex='1' marginLeft='5px'
                    onClick={() => {dispatch(openDevice({mode: 'create'}))}} >New Device</Button>
                </Flex>
            </Box>
        </Box>
        <PolicyModal/>
        <DeviceModal />
    </>;
}