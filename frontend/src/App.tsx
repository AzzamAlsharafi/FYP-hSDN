import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "./redux/hooks";
import { loadTopology, topologySelector } from "./redux/appSlice";
import { AppDispatch } from "./redux/store";

export default function App() {
  const topology = useAppSelector(topologySelector);
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
    <div style={{ width: '100vw', height: '100vh'}}>
      <pre>{JSON.stringify(topology, null, 2) }</pre>
    </div>
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