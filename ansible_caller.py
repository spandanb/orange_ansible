from ansible_wrapper import Runner
import os

os.environ["VAULT_PASS"] = "password"

runner = Runner(
    hosts={'contr': ['10.12.1.23'], 'agent':['10.12.1.26']},
    playbook='run.yaml', #path to playbook
    private_key_file='~/.ssh/id_rsa',
    run_data={'user_id':''}, #what is this for?
    become_pass='ubuntu',
    verbosity=1
)

stats = runner.run()

