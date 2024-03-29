import { Flex, IconButton, Spacer, Text } from "@chakra-ui/react";
import { deletePolicy, openPolicy, policiesSelector } from "../redux/appSlice";
import { useAppDispatch, useAppSelector } from "../redux/hooks";
import { getPolicyContent } from "../utils";
import { DeleteIcon, EditIcon } from "@chakra-ui/icons";

export default function PoliciesList() {
    const policies = useAppSelector(policiesSelector);
    const dispatch = useAppDispatch();

    return <>
        {policies.map((policy, _) => {
            const name = policy.type == 'flow' ? policy.name : 
                        policy.type == 'block' ? policy.target : 
                        policy.device;
            const content = getPolicyContent(policy)
            
            return <Flex key={`${policy.type}-${name}-${content}`}>
                <Text bg={`policy.${policy.type}`} w='80px' borderRadius='5px' margin='5px' paddingX='10px' paddingY='2px'
                textTransform='capitalize' textAlign='center'>
                    {policy.type}
                </Text>
                <Text margin='5px' paddingX='5px' paddingY='2px' fontWeight='bold'>
                    {name}
                </Text>
                <Text margin='5px' paddingX='5px' paddingY='2px'>
                    {content}
                </Text>
                <Spacer />
                <IconButton aria-label="edit" size='sm' icon={<EditIcon />} marginX='5px'
                onClick={() => {dispatch(openPolicy({mode: 'edit', editOriginal: policy}))}} />
                <IconButton aria-label="delete" size='sm' icon={<DeleteIcon />}
                onClick={() => {dispatch(deletePolicy(policy))}}/>
            </Flex>
        }
        )}
    </>;
}