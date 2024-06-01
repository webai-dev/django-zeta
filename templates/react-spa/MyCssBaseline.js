import { withStyles } from "@material-ui/core/styles";

const styles = theme => ({
  "@global": {
    h2: {
      ...theme.typography.h2
    }
  }
});

const MyCssBaseline = (props) => {
  return props.children;
}



export default withStyles(styles)(MyCssBaseline);