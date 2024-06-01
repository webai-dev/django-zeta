import React from 'react';

import useWebSocket from 'react-use-websocket';

import LoadingPage from '../LoadingPage';

const stages = {
{%- for stage_definition in module_definition.stage_definitions.all() %}
  "{{stage_definition.name}}": React.lazy(() => import('../Stage/{{module_definition.name}}{{stage_definition.name}}')),
{%- endfor %}
};

const Module{{module_definition.name}} = ({currentStageName}) => {
  const LoadingStage = props => <LoadingPage>Loading stage...</LoadingPage>;
  const CurrentStage = stages[currentStageName] || LoadingStage;

  return (
    <React.Suspense fallback={<LoadingStage />}>
      <CurrentStage />
    </React.Suspense>
  );
};

export default Module{{module_definition.name}};
