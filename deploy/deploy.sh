# A deployment script that pushes the linak-mqtt source code to a remote machine and then runs the application.
# The stdout from the application is captured to help with debugging.

target=$1
install_dependencies=$2

dir_application=/home/hronn/linak-mqtt

printf "Running deployment script, target is $target. Will install to $dir_application. Install dependencies = $install_dependencies\n"

# 1: Copy the application to the target.
printf "Copying linak-mqtt application...\n"
if [ "$install_dependencies" = true ] ; then
    poetry export -f requirements.txt --output requirements.txt
fi
scp -rq python/ requirements.txt hronn@$target:$dir_application

# 2: Update dependencies, if requested
if [ "$install_dependencies" = true ] ; then
    printf "Updating dependencies...\n"
    ssh hronn@$target "cd $dir_application && pip install -r requirements.txt"
fi

# 3: Run the application
printf "Running linak-mqtt application...\n--------------------------------------------------\n"
ssh hronn@$target "cd $dir_application && python -u python/__main_.py"