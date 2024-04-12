import { Button, Flex, Modal, ModalBody, ModalCloseButton, ModalContent, ModalFooter, ModalHeader, ModalOverlay, Text, useDisclosure } from "@chakra-ui/react";
import { useAppDispatch, useAppSelector } from "../redux/hooks";
import { addZone, nodesSelector } from "../redux/appSlice";
import MInput from "./mInput";
import { useState } from "react";

export default function MultiActionPanel() {
    const selectedNodes = useAppSelector(nodesSelector);
    const selectedDevices = selectedNodes.filter(node => node.type == 'device');
    const dispatch = useAppDispatch();

    const { isOpen, onOpen, onClose } = useDisclosure()
    const [zone, setZone] = useState<string>('');
    const isZoneInvalid = !Boolean(zone);


    return <>
        <Text fontSize='xl' fontWeight='bold' paddingBottom='5px'>Selected devices: {selectedDevices.length}</Text>
        <Flex paddingBottom='20px'>
            <Button flex='1' marginRight='5px'
            onClick={onOpen}>Add
                <Text bg={`policy.zone`} borderRadius='5px' margin='5px' paddingX='10px' paddingY='2px'
                textTransform='capitalize' textAlign='center'>
                    Zone
                </Text>
            </Button>
            <Button flex='1' marginLeft='5px'>Add
                <Text bg={`policy.route`} borderRadius='5px' margin='5px' paddingX='10px' paddingY='2px'
                textTransform='capitalize' textAlign='center'>
                    Route
                </Text>
            </Button>
        </Flex>

        <Modal isOpen={isOpen} onClose={onClose}>
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
                        onClose();
                        dispatch(addZone(zone))
                    }}>
                    Save
                    </Button>
                    <Button variant='ghost' onClick={() => {
                        setZone('');
                        onClose();
                    }}>Discard</Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
    </>;
}