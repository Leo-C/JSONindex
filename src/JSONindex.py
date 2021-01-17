import ijson
import re
import io
import os


#  proxy stream read-only limited to offsets start-end
# start is comprised an 0-based; end is excluded
# (like substring = string[start:end])
class SubStream(io.RawIOBase):
    """
    A Proxy that encapsulate a read-only Stream to access only a subpart
    (with dleimiter like a substring = string[start:end])
    """
    
    def __init__(self, s, start, stop):
        """
        Parameters
        ----------
        s : Stream
            the underlying stream
        start : int
            start position (0-based)
        stop : int
            end posistion (excluded)
        """
        
        self.__s = s
        self.__start = start
        self.__stop = stop
        
        if s.seekable():
            s.seek(start)
        else:
            cnt = 0
            while(cnt < start):
                s.read(1)
                cnt += 1
    
    def close(self):
        return self.__s.close()
    
    def get_closed(self):
        return self.__s.closed
    
    def fileno(self):
        return self.__s.fileno()
    
    def flush(self):
        raise io.UnsupportedOperation()
    
    def isatty(self):
        return self.__s.isatty()
    
    def readable(self):
        return self.__s.readable()
    
    def readline(self, size=-1):
        pos = self.__s.tell()
        max_size = max(self.__stop - pos, 0)
        if (size < 0):
            return self.__s.readline(max_size)
        else:
            max_size = min(max_size, size)
            return self.__s.readline(max_size)
    
    def readlines(self, hint=-1):
        cnt = 0
        lines = []
        
        while(True):
            line = self.readline()
            if len(line) == 0:
                break
            cnt += len(line)
            lines.append(line)
            if (hint > 0) and (cnt >= hint):
                break
        
        return lines
    
    def seek(self, offset, whence=os.SEEK_SET):
        if (whence == os.SEEK_SET):
            pos = self.__start + offset
        elif (whence == os.SEEK_CUR):
            pos = self.__s.tell()
            pos += offset
        elif (whence == os.SEEK_END):
            pos = self.__stop + offset
        
        self.__s.seek(max(min(pos, self.__stop), self.__start))
        
        return self.tell()
        
    def seekable(self):
        return self.__s.seekable()
    
    def tell(self):
        return self.__s.tell() - self.__start
    
    def truncate(self, size=None):
        raise io.UnsupportedOperation()
    
    def writable(self):
        return False
    
    def writelines(self, lines):
        raise io.UnsupportedOperation()
    
    def __del__(self):
        self.__s.close()
    
    def read(self, size=-1):
        pos = self.__s.tell()
        max_size = max(self.__stop - pos, 0)
        if (size < 0):
            return self.__s.read(max_size)
        else:
            max_size = min(max_size, size)
            return self.__s.read(max_size)
    
    def readall(self):
        return self.read(-1)
    
    def readinto(self, b):
        buf = self.read(len(b))
        b[0:len(buf)] = bytearray(buf, 'UTF-8') #copy
        return len(buf)
    
    def write(self, b):
        raise io.UnsupportedOperation()
    
    

# function used by buildJSONindex()
def match_prefix(prefix, re_patterns):
    for patt in re_patterns:
        m = patt.fullmatch(prefix)
        if m != None:
            return True
    
    return False


def buildJSONindex(fd_in, fd_out, static_prefixes = [], regexp_prefixes = []):
    """
    Scan (in 1-pass, in linear time) a JSON and minify it,
    returning a dictionary of desired prefixes with positions
    (of minified output).
    These positions can be used to random access a portion of a
    JSON using SubString class (i.e. loading with json.load())
    
    Parameters
    ----------
    fd_in : Stream
        byte-stream input for input JSON
    fd_out : Stream
        byte-stream output for minified JSON
    static_prefixes : list, optional
        a list of prefixes (used by ijson lib) to index
    regexp_prefixes : list, optional
        a list of regexp for prefixes (used by ijson lib) to index

    Returns
    -------
    Dict
        pos_start and pos_end positions associated to indexed prefixes
        (prefix used by ijson lib), in form:
        {"prefix" -> (pos_start, pos_end), ... }
    """
    
    #position pointer
    p = 0
    
    #create an hashset of static prefixes (for faster search)
    set_pre = set(static_prefixes)
    
    #create an hashset of pre-compiled regexp
    set_re = set()
    for regexp in regexp_prefixes:
        set_re.add(re.compile(regexp))
    
    index = {} #a list of indexed "prefix" -> {"start": pos_start, "end": pos_end}
    stack = [] #used for state of JSON parsing
    
    parser = ijson.parse(fd_in)
    for prefix, event, value in parser:
        if ((len(stack) > 0) and (stack[-1] == 'val')):
            if event not in ["end_map", "end_array"]:
                fd_out.write(b',') #write separation comma between values
                p += 1
            stack.pop()
        
        if event == 'start_map':
            fd_out.write(b'{')
            stack.append('val') # an object is a value
            stack.append(('map', p))
            p += 1
        elif event == 'end_map':
            fd_out.write(b'}')
            tag = stack.pop()
            p += 1
            if ((prefix in set_pre) or match_prefix(prefix, set_re)):
                index[prefix] = (tag[1], p)
        elif event == 'start_array':
            fd_out.write(b'[')
            stack.append('val') # an array is a value
            stack.append(('arr', p))
            p += 1
        elif event == 'end_array':
            fd_out.write(b']')
            tag = stack.pop()
            p += 1
            if ((prefix in set_pre) or match_prefix(prefix, set_re)):
                index[prefix] = (tag[1], p)
        elif event == 'map_key':
            val = bytes(value, "UTF-8")
            fd_out.write(b'"')
            fd_out.write(val)
            fd_out.write(b'":')
            p += (len(val)+3)
        elif event == 'null':
            fd_out.write(b'null')
            stack.append('val')
            p += 4
        elif event == 'boolean':
            if value:
                fd_out.write(b'true')
                p += 4
            else:
                fd_out.write(b'false')
                p += 5
            stack.append('val')
        elif event in ['integer', 'double', 'number']:
            val = bytes(str(value), "UTF-8")
            fd_out.write(val)
            stack.append('val')
            p += len(val)
        elif event == 'string':
            val = bytes(value, "UTF-8")
            fd_out.write(b'"')
            fd_out.write(val)
            fd_out.write(b'"')
            stack.append('val')
            p += (len(val)+2)
    
    return index
