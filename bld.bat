pip install .
cd ./baln/opt/CLANUtils/unix
cmake -G "MinGW Makefiles" ../src
make 
mkdir -p %PREFIX%/bin
mv ./bin/* %PREFIX%/bin
chmod u+x %PREFIX%/bin/*
