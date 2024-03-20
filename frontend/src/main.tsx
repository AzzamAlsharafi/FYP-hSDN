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
      address: '#00FF00',
      flow: '#FF0000',
      block: '#000000',
      route: '#0000FF',
      zone: '#FFFF00',
      disable: '#808080',
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
