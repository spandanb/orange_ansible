#!/bin/bash

ansible-playbook -i ./hosts run.yaml --extra-vars "filename=foobar"
