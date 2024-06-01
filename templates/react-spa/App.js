import React, { useMemo, useState } from 'react';

import useWebSocket from 'react-use-websocket';

import LoadingPage from './LoadingPage';
import Stint{{stint_definition.name}} from './Stint';

import MyCssBaseline from './MyCssBaseline'

export const AppContext = React.createContext();
export const ModuleContext = React.createContext();
export const BlockContext = React.createContext();

const protocol = window.location.protocol == 'https:' ? 'wss' : 'ws';
const href = window.location.href.replace(/\/$/, "");
const stint_gql_id = href.substring(href.lastIndexOf('/') + 1);

const App = props => {
  const [currentModuleName, setCurrentModuleName] = useState();
  const [currentStageName, setCurrentStageName] = useState();
  const [currentStageID, setCurrentStageID] = useState();
  const [currentStintID, setCurrentStintID] = useState();
  const [variables, setVariables] = useState();

  const wsOptions = useMemo(() => ({
    onError: error => console.log('onError', error),
    onMessage: socketMessage => { 
      for (const message of JSON.parse(socketMessage.data).messages) {
        switch(message.event) {
          case 'set_stint':
            setCurrentStintID(message.data);
            break
          case 'update_all_vars':
            setVariables(JSON.parse(message.data));
            break
          case 'current_module':
            setCurrentModuleName(message.data);
            break
          case 'current_stage':
            setCurrentStageName(message.data.current_stage);
            setCurrentStageID(message.data.current_stage_id);
            break
          case 'update_var':
            // clone state and then update
            // XXX: Team/Module variables must take into consideration duplicated variable names across scopes
            // XXX: We may just want to resend all variables due to lack of knowledge of team/module names
            setVariables((state) => {
              const newState = JSON.parse(JSON.stringify(state));
              newState[message.data.name] = message.data.value;
              return newState
          })
        }
      }
    },
    shouldReconnect: closeEvent => true,
    reconnectAttempts: 10,
    reconnectInterval: 3000,
  }), []);

  const wsUrl = `${protocol}://${window.location.host}/ws/webrunner/?stint_channel=${stint_gql_id}`;
  const [sendMessage, lastMessage, readyState, getWebSocket] = useWebSocket(wsUrl, wsOptions);
  const triggerWidgetEvent = (gqlID, name, event_type, value=null) => {
    sendMessage(JSON.stringify({
      event: "widget_event", 
      data: {
        gql_id: gqlID,
        name: name || '',
        event_type: event_type,
        stint_id: currentStintID,
        current_stage_id: currentStageID,
        value: value
      }
    }));
  };
  const triggerFormEvent = (gql_id, event_type, form_data) => {
    sendMessage(JSON.stringify({
      event: "form_event",
      data: {
        gql_id: gql_id,
        event_type: event_type,
        form_data: form_data
      }
    }));
  };

  return (
    readyState === 1 // websocket ready
    ? (
        <AppContext.Provider value={ {'triggerWidgetEvent': triggerWidgetEvent, 'triggerFormEvent': triggerFormEvent} }>
          <ModuleContext.Provider value={currentStageName}>
            <BlockContext.Provider value={variables}>
              <MyCssBaseline>
              <Stint{{stint_definition.name}} currentModuleName={currentModuleName} />
              </MyCssBaseline>
            </BlockContext.Provider>
          </ModuleContext.Provider>
        </AppContext.Provider>
      )
    : <LoadingPage>Loading websocket ...</LoadingPage>
  );
};

export default App;
