import { useEffect } from "react";
import { useAppDispatch } from "./redux/hooks";
import { loadConfig, loadTopology } from "./redux/appSlice";
import { AppDispatch } from "./redux/store";
import TopologyGraph from "./components/TopologyGraph";
import { Box } from "@chakra-ui/react";
import Panel from "./components/Panel";
import { ReactFlowProvider } from "reactflow";

export default function App() {
  const dispatch = useAppDispatch();
  
  // Fetch data periodically from API
  useEffect(() => {
    const interval = setInterval(() => {
      fetchTopology(dispatch);
      fetchConfig(dispatch);
    }, 1000);
    fetchTopology(dispatch);
    fetchConfig(dispatch);
    return () => clearInterval(interval);
  }, []);

  return <>
      <Box style={{ width: '100vw', height: '100vh'}}>
        <ReactFlowProvider>
          <TopologyGraph />
        </ReactFlowProvider>
      </Box>
      <Box position='absolute' top='10px' right='10px'>
        <Panel />
      </Box>
    </>;
}

const url = import.meta.env.VITE_URL;

function fetchTopology(dispatch: AppDispatch) {
  fetch(url + '/topology')
    .then((response) => {
      if (!response.ok) {
        console.error('Failed to fetch topology data: ', response);
        return;
      }

      response.json().then((data) => {
        dispatch(loadTopology(data));
      });
    })
}

function fetchConfig(dispatch: AppDispatch) {
  fetch(url + '/configurations')
    .then((response) => {
      if (!response.ok) {
        console.error('Failed to fetch configurations data: ', response);
        return;
      }

      response.json().then((data) => {
        dispatch(loadConfig(data));
      });
    })
}