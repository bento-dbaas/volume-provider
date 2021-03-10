[![Build Status](https://travis-ci.org/bento-dbaas/volume-provider.svg?branch=master)](https://travis-ci.org/bento-dbaas/volume-provider) [![Coverage Status](https://coveralls.io/repos/github/bento-dbaas/volume-provider/badge.svg?branch=master)](https://coveralls.io/github/bento-dbaas/volume-provider?branch=master)

## Volume Provider

### How to run
Native:
 - Copy the base env file to dev env file:
```shell
$cp .export-volume-provider-local-base.sh .export-volume-provider-local-dev.sh
```
 - Replace variables in `.export-volume-provider-local-dev.sh` file (or configure your local env).
 - install requirements:
```shell
$pip install -r requirements.txt
```
 - load environment variables: 
```shell
$source .export-volume-provider-local-dev.sh
```
   
 - run project: `$make run`

Docker Compose:
`todo`

### How to test

To test, you must run a local instance of mongodb `mongod --dbpath=/tmp`. then run the following command:

```shell
$make test
```
### Configure DBaaS:
Go to your `DBaaS local instance > DBaaaS_Credentials > Credentials` and point the `Volume Provider` Cretentials to your Volume provider instance (127.0.0.1:5000)
