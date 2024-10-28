import heapq
import json
import os
import struct
from collections import Counter
from datetime import datetime

# import matplotlib
from django.conf import settings
# from django.core.files.locks import lock
from django.http import JsonResponse
from django.shortcuts import render

import ctypes
# import matplotlib.pyplot as plt
# import networkx as nx
import threading

# 创建锁
lock = threading.Lock()


# Create your views here.

def cal(request):
    if request.method == 'POST':
        jsonstr = json.loads(request.body)
        calstr = jsonstr['expression']
        print(calstr)

        example = ctypes.CDLL("./tools/cal.dll")
        example.calculator.argtypes = [ctypes.c_char_p]
        example.calculator.restype = ctypes.c_double
        result = example.calculator(calstr.encode('utf-8'))
        print(result)
        return JsonResponse({'result': calstr + "=" + str(result)})

    else:
        return render(request, 'calculator.html')


class Node(object):
    def __init__(self, char=None, Freq=None, left=None, right=None):
        self.char = char
        self.Freq = Freq
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.Freq < other.Freq


def build_tree(Nodedic):
    heap = [Node(char, freq) for char, freq in Nodedic.items()]
    heapq.heapify(heap)

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        newNode = Node(char=None, Freq=left.Freq + right.Freq, left=left, right=right)
        heapq.heappush(heap, newNode)

    return heap[0]


def dfs_get_dic(node, prefix="", chardic=None):
    if chardic is None:
        chardic = {}
    if node is not None:
        if node.char is not None:
            chardic[node.char] = prefix
        dfs_get_dic(node.left, prefix + '0', chardic)
        dfs_get_dic(node.right, prefix + '1', chardic)
    return chardic


def file_with(uploaded_file, sefile: str):
    text = uploaded_file.read()
    Nodedic = Counter(text)
    print(Nodedic)
    tree_node = build_tree(Nodedic)
    chardic = dfs_get_dic(tree_node)
    # tmp = dfs_tree_dic(tree_node)
    # print(tmp)
    tmp = chardic
    bitcode = ''.join(chardic[ch] for ch in text)
    padding = 8 - len(bitcode) % 8
    bitcode += '0' * padding
    file_name = f'tree_{datetime.now().strftime("%Y%m%d_%H%M%S")}.bin'
    file_path = os.path.join(settings.MEDIA_ROOT, file_name)
    with open(file_path, 'wb') as f:
        selen = len(sefile)
        f.write(struct.pack('I', selen))
        f.write(sefile.encode())
        json_chardic = json.dumps(chardic)
        f.write(struct.pack('I', len(json_chardic.encode())))
        f.write(json_chardic.encode())
        f.write(struct.pack('I', padding))
        for i in range(0, len(bitcode), 8):
            byte = bitcode[i:i + 8]
            f.write(bytes([int(byte, 2)]))
    file_url = os.path.join(settings.MEDIA_URL, file_name) + f"?t={datetime.now().timestamp()}"
    return file_url, tmp


def unfile_with(uploaded_file):
    f = uploaded_file
    selen = struct.unpack('I', f.read(4))[0]
    se = f.read(selen).decode()
    dict_len = struct.unpack('I', f.read(4))[0]
    tmp = f.read(dict_len)
    print(tmp)
    chardic = json.loads(tmp.decode())
    padding = struct.unpack('I', f.read(4))[0]
    bit_string = ""
    byte = f.read(1)
    while byte:
        bits = bin(ord(byte))[2:].rjust(8, '0')
        bit_string += bits
        byte = f.read(1)
    bit_string = bit_string[:-padding]
    reversed_codes = {v: k for k, v in chardic.items()}
    print(reversed_codes)
    decoded_text = ""
    current_code = ""
    for bit in bit_string:
        current_code += bit
        if current_code in reversed_codes:
            decoded_text += reversed_codes[current_code]
            current_code = ""
    file_name = f'tree_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{se}'
    file_path = os.path.join(settings.MEDIA_ROOT, file_name)
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(decoded_text)
    file_url = os.path.join(settings.MEDIA_URL, file_name) + f"?t={datetime.now().timestamp()}"
    return file_url, chardic


def compress_file(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({'error': 'No file provided'}, status=400)
        file_name = uploaded_file.name
        file_extension = os.path.splitext(file_name)[1]
        fileurl, edges = file_with(uploaded_file, file_extension)
        response_data = {'file': fileurl}
        tmp = {chr(k): v for k, v in edges.items()}
        response_data['huffmanCodeDict'] = tmp
        print(response_data)
        return JsonResponse(response_data)
    else:
        return render(request, 'hfm.html')


def decompress_file(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({'error': 'No file provided'}, status=400)
        file_name = uploaded_file.name
        fileurl, uu = unfile_with(uploaded_file)
        response_data = {'file': fileurl}
        response_data['huffmanCodeDict'] = uu
        return JsonResponse(response_data)
    else:
        return render(request, 'hfm.html')
