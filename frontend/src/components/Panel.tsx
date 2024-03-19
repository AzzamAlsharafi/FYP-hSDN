import { Box, Text } from "@chakra-ui/react";
import { useAppSelector } from "../redux/hooks";
import { edgesSelector, nodesSelector } from "../redux/appSlice";
import SummaryPanel from "./SummaryPanel";
import NodePanel from "./NodePanel";

export default function Panel() {
    const selectedNodes = useAppSelector(nodesSelector);
    const selectedEdges = useAppSelector(edgesSelector);

    return (
        <Box bg='lightgrey' borderRadius='20px' minW='400px' padding='10px'>
            <Box bg='white' borderRadius='20px' padding='10px'>
                {selectedNodes.length == 0 ? <SummaryPanel /> 
                : selectedNodes.length == 1 ? <NodePanel node={selectedNodes[0]} /> 
                : <Text>MANY</Text>}
            </Box>
        </Box>
    );
}