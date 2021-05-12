docker volume create compare-vol
docker build -t compare .
docker run compare -v compare-vol:/src