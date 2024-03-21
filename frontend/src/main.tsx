import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ChakraProvider, extendTheme } from '@chakra-ui/react';
import { Provider } from 'react-redux';
import { store } from './redux/store';

// Colors used for drawing classic and SDN devices
const theme = extendTheme({
  colors: {
    bg: {
      classic: '#007FFF',
      sdn: '#F58536',
    },
    border: {
      classic: '#0050A0',
      sdn: '#A04E00',
    },
    policy: {
      address: '#68D391',
      flow: '#76E4F7',
      block: '#CBD5E0',
      route: '#63B3ED',
      zone: '#F6E05E',
      disable: '#FC8181',
    }
  }
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Provider store={store}>
      <ChakraProvider theme={theme}>
        <App/>
      </ChakraProvider>
    </Provider>
  </React.StrictMode>,
);
