class Request( dict ):
    
    def __init__( self, *args, **kwargs ):
        # method, path, host, port, schema, username, password, script, path,
        # query, fragment, request_version
        self.environ = {}
        dict.__init__( self, *args, **kwargs )

    body = property( lambda s : s._body, lambda s, v : setattr(s, '_body', v) )
    headers = property( lambda s : s.items() )
