import { Flex, Spacer, Text } from "@chakra-ui/react";
import { policiesSelector } from "../redux/appSlice";
import { useAppSelector } from "../redux/hooks";
import { getPolicyContent } from "../utils";

export default function PoliciesList() {
    const policies = useAppSelector(policiesSelector);

    return <>
        {policies.map((policy, _) => {
            const name = policy.type == 'flow' ? policy.name : policy.device;
            const content = getPolicyContent(policy)
            
            return <Flex key={`${policy.type}-${name}-${content}`}>
                <Text bg={`policy.${policy.type}`} borderRadius='5px' margin='5px' paddingX='10px' paddingY='2px'
                textTransform='capitalize'>
                    {policy.type}
                </Text>
                <Text margin='5px' paddingX='5px' paddingY='2px' fontWeight='bold'>
                    {name}
                </Text>
                <Text margin='5px' paddingX='5px' paddingY='2px'>
                    {content}
                </Text>
                <Spacer />
            </Flex>
        }
        )}
    </>;
}