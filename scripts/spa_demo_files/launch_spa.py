import os
import webbrowser

spa_address = f'{os.getcwd()}/react-spa/es5/'
tmp_file_name = 'bundle.html'

with open(f'{spa_address}/{tmp_file_name}', 'w') as f:
    f.write(
        """
<html>
    <body>
        <div id="container"></div>
        <script type="text/javascript">
"""
    )
    f.write(open(f'{spa_address}/browserify-bundle.js', 'r').read())
    f.write(
        """
        </script>
    </body>
</html>
"""
    )
webbrowser.open(f'file://{spa_address}/{tmp_file_name}')
