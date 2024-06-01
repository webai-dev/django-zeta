import React from 'react';

import useWebSocket from 'react-use-websocket';

import { ModuleContext } from './App';
import LoadingPage from './LoadingPage';

const modules = {
{%- for module_definition in module_definitions %}
  "{{module_definition.name}}": React.lazy(() => import('./Module/{{module_definition.name}}')),
{%- endfor %}
};

const Stint{{stint_definition.name}} = ({currentModuleName}) => {
  const LoadingModule = props => <LoadingPage>Loading module ...</LoadingPage>;
  const CurrentModule = modules[currentModuleName];

  return (
    CurrentModule 
    ? (<React.Suspense fallback={<LoadingModule />}>
        <ModuleContext.Consumer>
          { currentStageName => <CurrentModule currentStageName={currentStageName} /> }
        </ModuleContext.Consumer>
      </React.Suspense>)
    : <LoadingModule />
  );
};

export default Stint{{stint_definition.name}};
