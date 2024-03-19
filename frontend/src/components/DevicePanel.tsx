import { ListItem, Text, UnorderedList } from "@chakra-ui/react";
import { Device } from "../redux/appSlice";

export default function DevicePanel(props: {device: Device}) {
    const device = props.device;
    return (
        <>
            <Text fontSize='36' fontWeight='bold'>{device.name}</Text>
            <Text>TYPE: {device.type}</Text>
            <Text>PORTS: </Text>
            <UnorderedList>
                {device.ports.map((port, _) => 
                <ListItem key={device.name + port.interface_name + 'panel-item'}>
                    <Text>
                        {port.interface_name} - {port.hw_addr}
                    </Text>
                </ListItem>)}
            </UnorderedList>
        </>
    );
}