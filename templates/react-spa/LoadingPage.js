import React from 'react';

import Container from '@material-ui/core/Container';
import CircularProgress from '@material-ui/core/CircularProgress';
import Grid from '@material-ui/core/Grid';
import Paper from '@material-ui/core/Paper';
import Typography from '@material-ui/core/Typography';

const LoadingPage = props => (
  <Grid container direction='column' alignItems='center' justify='center'>
    <Paper>
      <Grid container direction='column' alignItems='center' justify='center'>
        <CircularProgress />
        <Typography variant='h3'>{props.children || 'Loading...'}</Typography>
      </Grid>
    </Paper>
  </Grid>
);

export default LoadingPage;
