import { ListItem, Text, UnorderedList } from "@chakra-ui/react";
import { useAppSelector } from "../redux/hooks";
import { topologySelector } from "../redux/appSlice";

export default function SummaryPanel() {
    const topology = useAppSelector(topologySelector);

    return (
        <>
            <Text fontSize='36' fontWeight='bold'>Network Summary</Text>
                <Text fontSize='24'>Devices: {topology.devices.length}</Text>
                <UnorderedList>
                    <ListItem>
                        <Text fontSize='20'>Classic: {topology.devices.filter(d => d.type == 'Classic').length}</Text>
                    </ListItem>
                    <ListItem>
                        <Text fontSize='20'>SDN: {topology.devices.filter(d => d.type == 'SDN').length}</Text>
                    </ListItem>
                </UnorderedList>
                <Text fontSize='24'>Links: {topology.links.length}</Text>
        </>
    );
}