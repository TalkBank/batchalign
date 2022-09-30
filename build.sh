pip install .
make -j8 -C ./baln/opt/CLANUtils/src/ 
mkdir -p $PREFIX/bin
mv ./baln/opt/CLANUtils/unix/bin/* $PREFIX/bin
chmod u+x $PREFIX/bin/*

