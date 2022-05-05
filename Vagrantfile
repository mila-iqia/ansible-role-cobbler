# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "generic/fedora34"

  config.vm.hostname = "cobbler-bootstrap"
  config.vm.define "cobbler" do |t|
    t.vm.hostname = "cobbler"
  end

  config.vm.synced_folder "./", "/vagrant"

  config.vm.provision "ansible_local" do |ansible|
    ansible.limit = "localhost,all"
    ansible.playbook = "tests/vagrant/package_role.yml"
    ansible.verbose = true
  end

  config.vm.provision "ansible_local" do |ansible|
    ansible.limit = "all"
    ansible.inventory_path = "tests/vagrant/inventory.yml"
    ansible.playbook = "tests/vagrant/provision.yml"
    ansible.verbose = true
  end

  # Create a public network, which generally matched to bridged network.
  # Bridged networks make the machine appear as another physical device on
  # your network.
  # config.vm.network "public_network", ip: "192.168.33.10"

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:8080" will access port 80 on the guest machine.
  # NOTE: This will enable public access to the opened port
  # config.vm.network "forwarded_port", guest: 80, host: 8080

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine and only allow access
  # via 127.0.0.1 to disable public access
  # config.vm.network "forwarded_port", guest: 80, host: 8080, host_ip: "127.0.0.1"
end
