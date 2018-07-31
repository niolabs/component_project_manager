# nio project manager component

A nio component providing functionality to get, clone, modify, remove blocks
within a nio-project-blocks structure

## Exposed endpoints

GET

* /project/blocks - returns information about the blocks that have been cloned
* /project/refresh?cfg_type=service - refresh service definitions
* /project/refresh?cfg_type=block - refresh block definitions
* /project/refresh?cfg_type=all - refresh service and block definitions

DELETE

* /project/blocks?(comma separated list of blocks to delete) - deletes the blocks specified

POST
* /project/blocks - clones a block, expected body format is:
```python
{
    "url": "block_url",
    "branch": "block_branch",
    "tag": "block_tag",
    "path": "block_path"
}
```

if no *url* is specified in *body*, then interpret it as block updates, the following urls can be used:

/project/blocks?twitter&util or

/project/blocks?twitter,util

## Configuration

- None


## Dependencies

- None
