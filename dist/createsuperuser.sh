# split sub-directory this file is in
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SUBDIR=(${DIR//// })
# name of container is sub-directory + -web-1 if no name is given to docker-compose
CONTAINER=${SUBDIR[-1]}-web-1
# call django command to create superuser insiode container
docker exec -it $CONTAINER python manage.py createsuperuser
