import { useEffect } from "react";
import { useAppDispatch } from "./redux/hooks";
import { loadTopology } from "./redux/appSlice";
import { AppDispatch } from "./redux/store";
import TopologyGraph from "./components/TopologyGraph";
import { Box } from "@chakra-ui/react";

export default function App() {
  const dispatch = useAppDispatch();
  
  // Fetch data periodically from API
  useEffect(() => {
    const interval = setInterval(() => {
      fetchTopology(dispatch);
    }, 1000);
    fetchTopology(dispatch);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box style={{ width: '100vw', height: '100vh'}}>
      <TopologyGraph />
    </Box>
  );
}

function fetchTopology(dispatch: AppDispatch) {
  fetch('http://127.0.0.1:8000/topology')
    .then((response) => {
      if (!response.ok) {
        console.error('Failed to fetch topology data: ', response);
        return;
      }

      response.json().then((data) => {
        console.log('Fetched topology data: ', data);
        dispatch(loadTopology(data));
      });
    })
}