# bridgeSetup

sudo iptables -t nat -A POSTROUTING -s 172.17.0.0/16 -o wg1 -j MASQUERADE
sudo apt install iptables-persistent
sudo netfilter-persistent save
