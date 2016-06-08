import os
from tempfile import NamedTemporaryFile
from ansible.inventory import Inventory
from ansible.vars import VariableManager
from ansible.parsing.dataloader import DataLoader
from ansible.executor import playbook_executor
from ansible.utils.display import Display
import sys

#Take from: https://serversforhackers.com/running-ansible-2-programmatically

#What is this for?
os.environ["VAULT_PASS"] = "password"

class Options(object):
    """
    Options class to replace Ansible OptParser
    """
    def __init__(self, verbosity=None, inventory=None, listhosts=None, subset=None, module_paths=None, extra_vars=None,
                 forks=None, ask_vault_pass=None, vault_password_files=None, new_vault_password_file=None,
                 output_file=None, tags=None, skip_tags=None, one_line=None, tree=None, ask_sudo_pass=None, ask_su_pass=None,
                 sudo=None, sudo_user=None, become=None, become_method=None, become_user=None, become_ask_pass=None,
                 ask_pass=None, private_key_file=None, remote_user=None, connection=None, timeout=None, ssh_common_args=None,
                 sftp_extra_args=None, scp_extra_args=None, ssh_extra_args=None, poll_interval=None, seconds=None, check=None,
                 syntax=None, diff=None, force_handlers=None, flush_cache=None, listtasks=None, listtags=None, module_path=None):
        self.verbosity = verbosity
        self.inventory = inventory
        self.listhosts = listhosts
        self.subset = subset
        self.module_paths = module_paths
        self.extra_vars = extra_vars
        self.forks = forks
        self.ask_vault_pass = ask_vault_pass
        self.vault_password_files = vault_password_files
        self.new_vault_password_file = new_vault_password_file
        self.output_file = output_file
        self.tags = tags
        self.skip_tags = skip_tags
        self.one_line = one_line
        self.tree = tree
        self.ask_sudo_pass = ask_sudo_pass
        self.ask_su_pass = ask_su_pass
        self.sudo = sudo
        self.sudo_user = sudo_user
        self.become = become
        self.become_method = become_method
        self.become_user = become_user
        self.become_ask_pass = become_ask_pass
        self.ask_pass = ask_pass
        self.private_key_file = private_key_file
        self.remote_user = remote_user
        self.connection = connection
        self.timeout = timeout
        self.ssh_common_args = ssh_common_args
        self.sftp_extra_args = sftp_extra_args
        self.scp_extra_args = scp_extra_args
        self.ssh_extra_args = ssh_extra_args
        self.poll_interval = poll_interval
        self.seconds = seconds
        self.check = check
        self.syntax = syntax
        self.diff = diff
        self.force_handlers = force_handlers
        self.flush_cache = flush_cache
        self.listtasks = listtasks
        self.listtags = listtags
        self.module_path = module_path

class InventoryWrapper(object):
    """
    Class that encapsulates an inventoy and 
    provides various utiliy functions.
    """
    
    def __init__(self, hosts):
        """
        NB: hosts can be dict, list, str
        """
        self.hosts = hosts

    def __str__(self):
        if type(self.hosts) is str:
            return "[run_hosts]\n{}".format(self.hosts)

        elif type(self.hosts) is list:
            inv = "[run_hosts]\n"
            inv += "\n".join(["{}".format(h) for h in self.hosts])
            return inv

        elif type(self.hosts) is dict:
            inv = ""
            for group, nodes in self.hosts.items():
                inv += "[{}]\n".format(group)
                inv += "\n".join(["{}".format(n) for n in nodes])
                inv += "\n"
            return inv
    
    def host_list(self):
        """
        Returns a list of host addresses 
        """
        if type(self.hosts) is str:
            return [self.hosts]
        elif type(self.hosts) is list:
            return self.hosts
        else:
            return self.host.values()

        
class Runner(object):

    def __init__(self, 
                 hosts=None, 
                 playbook=None, 
                 remote_user='ubuntu',
                 private_key_file='~/.ssh/id_rsa',
                 become_pass='', 
                 verbosity=0, 
                 extra_vars={}):
        """
        Arguments:
            hosts:- The hosts. This can be either IP string, e.g. ["10.1.1.1"],
                        list of IPs, ["10.1.1.1", "10.1.1.5"],
                        a map of group name to list of members, e.g. {"contr":["10.1.1.1"], "agent":["10.1.1.5"]}
            playbook:- is the path to the playbook file
            become_pass:- seems like the password
                   for priviledge escalation 

        """
        if not hosts or not playbook:
            raise ValueError("hosts and playbook arguments must be defined")

        self.run_data = extra_vars

        self.options = Options()
        self.options.private_key_file = os.path.expanduser(private_key_file)
        self.options.verbosity = verbosity
        self.options.connection = 'ssh'  # Need a connection type "smart" or "ssh"
        self.options.become = True
        self.options.become_method = 'sudo'
        self.options.become_user = 'root'
        self.options.remote_user = remote_user

        # Set global verbosity
        self.display = Display()
        self.display.verbosity = self.options.verbosity
        # Executor appears to have it's own
        # verbosity object/setting as well
        playbook_executor.verbosity = self.options.verbosity

        # Become Pass Needed if not logging in as user root
        passwords = {'become_pass': become_pass}

        # Gets data from YAML/JSON files
        self.loader = DataLoader()
        self.loader.set_vault_password(os.environ['VAULT_PASS'])

        # All the variables from all the various places
        self.variable_manager = VariableManager()
        self.variable_manager.extra_vars = self.run_data

        # Parse hosts, I haven't found a good way to
        # pass hosts in without using a parsed template :(
        # (Maybe you know how?)
        self.hosts = NamedTemporaryFile(delete=False, dir=os.getcwd())
        self.inventory_wrapper = InventoryWrapper(hosts)
        self.hosts.write(str(self.inventory_wrapper))
        self.hosts.close()

        # Set inventory, using most of above objects
        self.inventory = Inventory(loader=self.loader, variable_manager=self.variable_manager, host_list=self.hosts.name)

        self.variable_manager.set_inventory(self.inventory)

        # Setup playbook executor, but don't run until run() called
        self.pbex = playbook_executor.PlaybookExecutor(
            playbooks=[playbook],
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            passwords=passwords)

    def run(self):
        # Results of PlaybookExecutor
        self.pbex.run()
        stats = self.pbex._tqm._stats

        # Test if success for record_logs
        run_success = True
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)
            if t['unreachable'] > 0 or t['failures'] > 0:
                run_success = False

        # Dirty hack to send callback to save logs with data we want
        # Note that function "record_logs" is one I created and put into
        # the playbook callback file
        #FIXME: get rid of the following, since this is not being used
        self.pbex._tqm.send_callback(
            'record_logs',
            user_id=None, #self.run_data['user_id'],
            success=run_success
        )

        # Remove created temporary files
        os.remove(self.hosts.name)

        return stats

def playbook(playbook=None, hosts=None, 
             private_key_file='~/.ssh/id_rsa', 
             verbosity=1, 
             remote_user='ubuntu', 
             extra_vars={}):
    """
    Calls a playbook specified by the user.
    Utility function that wraps instantiation of Runner object 
        and invokation of run method.

    Arguments:-
        playbook:- path to playbook
        host:-
    """
    runner = Runner(
        hosts=hosts,
        playbook=playbook,
        private_key_file=private_key_file,
        verbosity=verbosity,
        remote_user=remote_user,
        extra_vars=extra_vars
    )
    stats = runner.run()
    #Stats is not a useful object to return
    return {host:stats.summarize(host)
            for host in runner.inventory_wrapper.host_list()}

"""
TODO 
1)username is hardcoded to ubuntu
  Need way to better express hosts file
"""

"""
roles dir in same dir as script
playbooks pb_dir also in the same dir

VAULT_PASS envvar
"""
if __name__ == "__main__":
    print playbook(
        hosts='10.12.1.17',
        playbook='run.yaml',
        extra_vars={'filename':'yahhoo'}
    ) 

