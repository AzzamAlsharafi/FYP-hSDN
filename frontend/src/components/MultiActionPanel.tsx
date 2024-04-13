import { Button, Flex, FormControl, FormLabel, Modal, ModalBody, ModalCloseButton, ModalContent, ModalFooter, ModalHeader, ModalOverlay, Radio, RadioGroup, Stack, Text, useDisclosure } from "@chakra-ui/react";
import { useAppDispatch, useAppSelector } from "../redux/hooks";
import { addRoute, addZone, flowsSelector, nodesSelector, topologySelector } from "../redux/appSlice";
import MInput from "./mInput";
import { useMemo, useState } from "react";
import { MSelect } from "./mSelect";
import { calculateRoutes } from "../utils";

export default function MultiActionPanel() {
    const selectedNodes = useAppSelector(nodesSelector);
    const selectedDevices = selectedNodes.filter(node => node.type == 'device');
    const topology = useAppSelector(topologySelector);
    const flows = useAppSelector(flowsSelector);
    const dispatch = useAppDispatch();

    const { isOpen: zoneIsOpen, onOpen: zoneOnOpen, onClose: zoneOnClose } = useDisclosure()
    const [zone, setZone] = useState<string>('');
    const isZoneInvalid = !Boolean(zone);

    const { isOpen: routeIsOpen, onOpen: routeOnOpen, onClose: routeOnClose } = useDisclosure()
    const [routeFlow, setRouteFlow] = useState<string>('');
    const isRouteInvalid = !Boolean(routeFlow);
    const routes = useMemo(() => calculateRoutes(topology, selectedDevices.map(d => d.id)), [topology, selectedDevices]);
    const [route, setRoute] = useState('0');

    return <>
        <Text fontSize='xl' fontWeight='bold' paddingBottom='5px'>Selected devices: {selectedDevices.length}</Text>
        <Flex paddingBottom='20px'>
            <Button flex='1' marginRight='5px'
            onClick={zoneOnOpen}>Add
                <Text bg={`policy.zone`} borderRadius='5px' margin='5px' paddingX='10px' paddingY='2px'
                textTransform='capitalize' textAlign='center'>
                    Zone
                </Text>
            </Button>
            <Button flex='1' marginLeft='5px'
            onClick={routeOnOpen}>Add
                <Text bg={`policy.route`} borderRadius='5px' margin='5px' paddingX='10px' paddingY='2px'
                textTransform='capitalize' textAlign='center'>
                    Route
                </Text>
            </Button>
        </Flex>

        <Modal isOpen={zoneIsOpen} onClose={zoneOnClose}>
            <ModalOverlay />
            <ModalContent>
                <ModalHeader>Add Zone</ModalHeader>
                <ModalCloseButton />
                <ModalBody>
                    <MInput label='Name' placeholder='Type zone name' value={zone}
                    onChange={(e) => {setZone(e.target.value)}} isInvalid={isZoneInvalid}/>
                </ModalBody>

                <ModalFooter>
                    <Button colorScheme='blue' mr={3} isDisabled={isZoneInvalid} onClick={() => {
                        zoneOnClose();
                        dispatch(addZone(zone))
                    }}>
                    Save
                    </Button>
                    <Button variant='ghost' onClick={() => {
                        setZone('');
                        zoneOnClose();
                    }}>Discard</Button>
                </ModalFooter>
            </ModalContent>
        </Modal>

        <Modal isOpen={routeIsOpen} onClose={routeOnClose}>
            <ModalOverlay />
            <ModalContent>
                <ModalHeader>Add Route</ModalHeader>
                <ModalCloseButton />
                <ModalBody>
                    <MSelect label="Route Flow" value={routeFlow} options={flows}
                        onChange={(e) => setRouteFlow(e.target.value)}
                        isInvalid={isRouteInvalid}/>
                    
                    <FormControl padding='10px 0px'>
                        <FormLabel>Select Route</FormLabel>
                        <RadioGroup value={route} onChange={setRoute}>
                            <Stack>
                                {routes.map((r, i) => (
                                    <Radio key={r} value={i.toString()}>{r}</Radio>
                                ))}
                            </Stack>
                        </RadioGroup>
                    </FormControl>
                </ModalBody>

                <ModalFooter>
                    <Button colorScheme='blue' mr={3} isDisabled={isRouteInvalid} onClick={() => {
                        routeOnClose();
                        dispatch(addRoute({flow: routeFlow, route: routes[parseInt(route)]}));
                    }}>
                    Save
                    </Button>
                    <Button variant='ghost' onClick={() => {
                        setRouteFlow('');
                        setRoute('0');
                        routeOnClose();
                    }}>Discard</Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
    </>;
}