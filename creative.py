# coding: utf-8

try:
    from qiskit import ClassicalRegister, QuantumRegister, QuantumCircuit, get_backend, available_backends, execute
    from qiskit import register
except:
    print("Warning: QISKit is not installed\n         This won't be a problem if you only run from existing data")

import numpy as np
import random
import matplotlib.pyplot as plt
import os
import copy
import networkx as nx

try:
    import sys
    sys.path.append("../") # go to parent dir
    import Qconfig
    qx_config = {
        "APItoken": Qconfig.APItoken,
        "url": Qconfig.config['url']}
    #set api
    register(qx_config['APItoken'], qx_config['url'])
except Exception as e:
    print("Warning: Credentials required for using remote IBMQ devices hae not been set up")

    
class ladder:
    """An integer implemented on a single qubit. Addition and subtraction are implemented via partial NOT gates."""
    
    def __init__(self,d):
        """Create a new ladder object. This has the attribute `value`, which is an int that can be 0 at minimum and the supplied value `d` at maximum. This value is initialized to 0."""
        self.d = d
        self.qr = QuantumRegister(1)
        self.cr = ClassicalRegister(1)
        self.qc = QuantumCircuit(self.qr, self.cr)
        
    def add(self,delta):
        """Changes value of ladder object by the given amount `delta`. This is initially done by addition, but it changes to subtraction once the maximum value of `d` is reached. It will then change back to addition once 0 is reached, and so on.
        
        delta = Amount by which to change the value of the ladder object. Can be int or float."""
        self.qc.rx(np.pi*delta/self.d,self.qr[0])
        
    def value(self,backend='local_qasm_simulator',shots=1024):
        """Returns the current version of the ladder operator as an int. If floats have been added to this value, the sum of all floats added thus far are rounded.
        
        backend = A string specifying a backend. The noisy behaviour from a real device will result in some randomness in the value given, and can lead to the reported value being less than the true value on average. These effects will be more evident for high `d`.
        shots = Number of shots used when extracting results from the qubit. A low value will result in randomness in the value given. This should be neglible when the value is a few orders of magnitude greater than `d`. """  
        temp_qc = copy.deepcopy(self.qc)
        temp_qc.barrier(self.qr)
        temp_qc.measure(self.qr,self.cr)
        job = execute(temp_qc, backend=get_backend(backend), shots=shots)
        if '1' in job.result().get_counts():
            p = job.result().get_counts()['1']/shots
        else:
            p = 0
        delta = round(2*np.arcsin(np.sqrt(p))*self.d/np.pi)
        return int(delta)

    
class twobit:
    """An object that can store a single boolean value, but can do so in two incompatible ways. It is implemented on a single qubit using two complementary measurement bases."""
    
    def __init__(self):
        """Create a twobit object, initialized to give a random boolean value for both measurement types."""
        self.qr = QuantumRegister(1)
        self.cr = ClassicalRegister(1)
        self.qc = QuantumCircuit(self.qr, self.cr)
        self.prepare({'Y':None})
        
    def prepare(self,state):
        """Supplying `state={basis,b}` prepares a twobit with the boolean `b` stored using the measurement type specified by `basis` (which can be 'X' or 'Z').
        
        Supplying `basis='Y'` (and arbitrary `b`) will result in the twobit giving a random result for both measurement types. """
        self.qc = QuantumCircuit(self.qr, self.cr)
        if 'Y' in state:
            self.qc.h(self.qr[0])
            self.qc.s(self.qr[0])
        elif 'X' in state:
            if state['X']:
                self.qc.x(self.qr[0])
            self.qc.h(self.qr[0])
        elif 'Z' in state:
            if state['Z']:
                self.qc.x(self.qr[0])
                
    def value (self,basis,backend='local_qasm_simulator',shots=1024,mitigate=True):
        """Extracts the boolean value for the given measurement type. The twobit is also reinitialized to ensure that the same value would if the same call to `measure()` was repeated.
        
        basis = 'X' or 'Z', specifying the desired measurement type.
        backend = A string specifying a backend. The noisy behaviour from a real device will result in some randomness in the value given, even if it has been set to a definite value for a given measurement type. This effect can be reduced using `mitigate=True`.
        shots = Number of shots used when extracting results from the qubit. A value of greater than 1 only has any effect for `mitigate=True`, in which case larger values of `shots` allow for better mitigation.
        mitigate = Boolean specifying whether mitigation should be applied. If so the values obtained over `shots` samples are considered, and the fraction which output `True` is calculated. If this is more than 90%, measure will return `True`. If less than 10%, it will return `False`, otherwise it returns a random value using the fraction as the probability."""
        if basis=='X':
            self.qc.h(self.qr[0])
        self.qc.barrier(self.qr)
        self.qc.measure(self.qr,self.cr)
        job = execute(self.qc, backend=get_backend(backend), shots=shots)
        stats = job.result().get_counts()
        if '1' in stats:
            p = stats['1']/shots
        else:
            p = 0
        if mitigate:
            if p<0.1:
                p = 0
            elif p>0.9:
                p = 1
        measured_value = ( p>random.random() )
        self.prepare({basis:measured_value})
        
        return measured_value

        
def bell_correlation (basis,backend='local_qasm_simulator',shots=1024):
    """Prepares a rotated Bell state of two qubits. Measurement is done in the specified basis for each qubit. The fraction of results for which the two qubits agree is returned.
    
    basis = String specifying measurement bases. 'XX' denotes X measurement on each qubit, 'XZ' denotes X measurement on qubit 0 and Z on qubit 1, vice-versa for 'ZX', and 'ZZ' denotes 'Z' measurement on both.
    backend = A string specifying a backend. The noisy behaviour from a real device will result in the correlations being less strong than in the ideal case.
    shots = Number of shots used when extracting results from the qubit. For shots=1, the returned value will randomly be 0 (if the results for the two qubits disagree) or 1 (if they agree). For large shots, the returned value will be probability for this random process.
    """
    qr = QuantumRegister(2)
    cr = ClassicalRegister(2)
    qc = QuantumCircuit(qr,cr)

    qc.h( qr[0] )
    qc.cx( qr[0], qr[1] )
    qc.ry( np.pi/4, qr[1])
    qc.h( qr[1] )
    #qc.x( qr[0] )
    #qc.z( qr[0] )
    
    for j in range(2):
        if basis[j]=='X':
            qc.h(qr[j])

    qc.barrier(qr)
    qc.measure(qr,cr)
    
    job = execute(qc, backend=get_backend(backend), shots=shots)
    stats = job.result().get_counts()
    
    P = 0
    for string in stats:
        p = stats[string]/shots
        if string in ['00','11']:
            P += p
            
    return P

def bitstring_superposer (strings,backend='local_qasm_simulator',shots=1024):
    """Prepares the superposition of the two given n bit strings. The number of qubits used is equal to the length of the string. The superposition is measured, and the process repeated many times. A dictionary with the fraction of shots for which each string occurred is returned.
    
    string = List of two binary strings. If the list has more than two elements, all but the first two are ignored.
    backend = A string specifying a backend. The noisy behaviour from a real device will result in strings other than the two supplied occuring with non-zero fraction.
    shots = Number of times the process is repeated to calculate the fractions. For shots=1, only a single randomnly generated bit string is return (as the key of a dict)."""
    
    # make it so that the input is a list of list of strings, even if it was just a list of strings
    strings_list = []
    if type(strings[0])==str:
        strings_list = [strings]
    else:
        strings_list = strings
    
    batch = []
    for strings in strings_list:
        
        # find the length of the longest string, and pad any that are shorter
        num = 0
        for string in strings:
            num = max(len(string),num)
        for string in strings:
            string = '0'*(num-len(string)) + string
        
        qr = QuantumRegister(num)
        cr = ClassicalRegister(num)
        qc = QuantumCircuit(qr,cr)

        if len(strings)==2**num:
            for n in range(num):
                qc.h(qr[n])
        else:
            diff = []
            for bit in range(num):
                if strings[0][bit]==strings[1][bit]:
                    if strings[0][bit]=='1':
                        qc.x(qr[bit])
                if strings[0][bit]!=strings[1][bit]:
                    diff.append(bit)
            if diff:
                qc.h(qr[diff[0]])
                for bit in diff[1:]:
                    qc.cx(qr[diff[0]],qr[bit])
                for bit in diff:
                    if strings[0][bit]=='1':
                        qc.x(qr[bit])

        qc.barrier(qr)
        qc.measure(qr,cr)
        
        batch.append(qc)

    job = execute(batch, backend=get_backend(backend), shots=shots)
    
    stats_raw_list = []
    for j in range(len(strings_list)):
        stats_raw_list.append( job.result().get_counts(batch[j]) )

    stats_list = []
    for stats_raw in stats_raw_list:
        stats = {}
        for string in stats_raw:
            stats[string[::-1]] = stats_raw[string]/shots
        stats_list.append(stats)
    
    # if only one instance was given, output dict rather than list with a single dict
    if len(stats_list)==1:
        stats_list = stats_list[0]

    return stats_list
    
def emoticon_superposer (emoticons,backend='local_qasm_simulator',shots=1024,figsize=(20,20)):
    """Creates superposition of two emoticons.
    
    A dictionary is returned, which supplies the relative strength of each pair of ascii characters in the superposition. An image representing the superposition, with each pair of ascii characters appearing with an weight that represents their strength in the superposition, is also created and saved.
    
    emoticons = A list of two strings, each of which is composed of two ascii characters, such as [ ";)" , "8)" ].
    backend = A string specifying a backend. The noisy behaviour from a real device will result in emoticons other than the two supplied occuring with non-zero strength.
    shots = Number of times the process is repeated to calculate the fractions used as strengths. For shots=1, only a single randomnly generated emoticon is return (as the key of the dict)."""
    
    # make it so that the input is a list of list of strings, even if it was just a list of strings
    if type(emoticons[0])==str:
        emoticons_list = [emoticons]
    else:
        emoticons_list = emoticons
        
    strings = []
    for emoticons in emoticons_list:
        string = []
        for emoticon in emoticons:
            bin4emoticon = ""
            for character in emoticon:
                bin4char = bin(ord(character))[2:]
                bin4char = (8-len(bin4char))*'0'+bin4char
                bin4emoticon += bin4char
            string.append(bin4emoticon)
        strings.append(string)
        
    stats = bitstring_superposer(strings,backend=backend,shots=shots)
    
    # make a list of dicts from stats
    if type(stats) is dict:
        stats_list = [stats]
    else:
        stats_list = stats
        
    ascii_stats_list = []
    for stats in stats_list:
        fig = plt.figure()
        ax=fig.add_subplot(111)
        plt.rc('font', family='monospace')
        ascii_stats = {}
        for string in stats:
            char = chr(int( string[0:8] ,2)) # get string of the leftmost 8 bits and convert to an ASCII character
            char += chr(int( string[8:16] ,2)) # do the same for string of rightmost 8 bits, and add it to the previous character
            prob = stats[string] # fraction of shots for which this result occurred
            ascii_stats[char] = prob
            # create plot with all characters on top of each other with alpha given by how often it turned up in the output
            try:
                plt.annotate( char, (0.5,0.5), va="center", ha="center", color = (0,0,0, prob ), size = 300)
            except:
                pass
        ascii_stats_list.append(ascii_stats)

        plt.axis('off')
        plt.show()
    
    # if only one instance was given, output dict rather than list with a single dict
    if len(ascii_stats_list)==1:
        ascii_stats_list = ascii_stats_list[0]
    
    return ascii_stats_list


def image_superposer (all_images,images,backend='local_qasm_simulator',shots=1024,figsize=(20,20)):
    """Creates superposition of two images from a set of images.
    
    A dictionary is returned, which supplies the relative strength of each pair of ascii characters in the superposition. An image representing the superposition, with each of the original aimages appearing with an weight that represents their strength in the superposition, is also created and saved.
    
    all_images = List of strings that are filenames for a set of images.  The files should be located in 'images/<filename>.png.
    images = List of strings for image files to be superposed. This can either contain the strings for two files, or for all in all_images. Other options are not currently supported.
    backend = A string specifying a backend. The noisy behaviour from a real device will result in images other than those intended appearing with non-zero strength.
    shots = Number of times the process is repeated to calculate the fractions used as strengths. For shots=1, only a single randomnly generated emoticon is return (as the key of the dict)."""
    image_num = len(all_images)
    bit_num = int(np.ceil( np.log2(image_num) ))
    all_images += [None]*(2**bit_num-image_num)
    
    # make it so that the input is a list of list of strings, even if it was just a list of strings
    if type(images[0])==str:
        images_list = [images]
    else:
        images_list = images
    
    strings = []
    for images in images_list:
        string = []
        for image in images:
            bin4pic = "{0:b}".format(all_images.index(image))
            bin4pic = '0'*(bit_num-len(bin4pic)) + bin4pic
            string.append( bin4pic )
        strings.append(string)
    
    full_stats = bitstring_superposer(strings,backend=backend,shots=shots)
        
    # make a list of dicts from stats
    if type(full_stats) is dict:
        full_stats_list = [full_stats]
    else:
        full_stats_list = full_stats
    
    stats_list = []
    for full_stats in full_stats_list:
        Z = 0
        for j in range(image_num):
            string = "{0:b}".format(j)
            string = '0'*(bit_num-len(string)) + string
            if string in full_stats:
                Z += full_stats[string]    
        stats = {}
        for j in range(image_num):
            string = "{0:b}".format(j)
            string = '0'*(bit_num-len(string)) + string
            if string in full_stats:
                stats[string] = full_stats[string]/Z
        stats_list.append(stats)
            
        # sort from least to most likely and create corresponding lists of the strings and fractions
        sorted_strings = sorted(stats,key=stats.get)
        sorted_fracs = sorted(stats.values())
        n = len(stats)
        # construct alpha values such that the final image is a weighted average of the images specified by the keys of `stats`
        alpha = [ sorted_fracs[0] ]
        for j in range(0,n-1):
            alpha.append( ( alpha[j]/(1-alpha[j]) ) * ( sorted_fracs[j+1] / sorted_fracs[j] ) )

        fig, ax = plt.subplots(figsize=figsize)
        for j in reversed(range(n)):
            filename = all_images[int(sorted_strings[j],2)]
            if filename:
                image = plt.imread("images/"+filename+".png")
                plt.imshow(image,alpha=alpha[j])
        plt.axis('off')
        plt.show()
    
    image_stats_list = []
    for stats in stats_list:
        image_stats = {}
        for string in stats:
            image_stats[ all_images[int(string,2)] ] = stats[string]
        image_stats_list.append(image_stats)
    
    # if only one instance was given, output dict rather than list with a single dict
    if len(image_stats_list)==1:
        image_stats_list = image_stats_list[0]
    
    return image_stats_list


class layout:
    
    def __init__(self,device):

        if device in ['ibmqx2', 'ibmqx4', 'ibmqx5']:
                        
            backend = get_backend(device)
            self.num = backend.configuration['n_qubits']
            coupling = backend.configuration['coupling_map']
            self.pairs = {}
            char = 65
            for pair in coupling:
                self.pairs[chr(char)] = pair
                char += 1
            if device in ['ibmqx2','ibmqx4']:
                self.pos = { 0: [1,1], 1: [1,0], 2: [0.5,0.5], 3: [0,0], 4: [0,1] }        
            elif device=='ibmqx5':
                self.pos = { 0: [0,0], 1: [0,1],  2: [1,1],  3: [2,1],  4: [3,1],  5: [4,1],  6: [5,1],  7: [6,1],
8: [7,1], 9: [7,0], 10: [6,0], 11: [5,0], 12: [4,0], 13: [3,0], 14: [2,0], 15: [1,0] }
            
        elif type(device) is list:
            
            Lx = device[0]
            Ly = device[1]
            self.num = Lx*Ly
            self.pairs = {}
            char = 65
            for x in range(Lx-1):
                for y in range(Ly):
                    n = x + y*Ly
                    m = n+1
                    self.pairs[chr(char)] = [n,m]
                    char += 1
            for x in range(Lx):
                for y in range(Ly-1):
                    n = x + y*Ly
                    m = n+Ly
                    self.pairs[chr(char)] = [n,m]
                    char += 1
            self.pos = {}
            for x in range(Lx):
                for y in range(Ly):
                    n = x + y*Ly
                    self.pos[n] = [x,y]
        else:
                
            print("Error: Device not recognized.\nMake sure it is a list of two integers (to specify a grid) or one of the supported IBM devices ('ibmqx2', 'ibmqx4' and 'ibmqx5').")
        
        for pair in self.pairs:
            self.pos[pair] = [(self.pos[self.pairs[pair][0]][j] + self.pos[self.pairs[pair][1]][j])/2 for j in range(2)]
  
    def calculate_probs(self,raw_stats):
        
        Z = 0
        for string in raw_stats:
            Z += raw_stats[string]
        stats = {}
        for string in raw_stats:
            stats[string] = raw_stats[string]/Z
        
        probs = {}
        for n in self.pos:
            probs[n] = 0
        
        for string in stats:
            for n in range(self.num):
                if string[-n-1]=='1':
                    probs[n] += stats[string]
            for pair in self.pairs: 
                if string[-self.pairs[pair][0]-1]!=string[-self.pairs[pair][1]-1]:
                    probs[pair] += stats[string]
            
        return probs
                    
    def plot(self,probs={},labels={},colors={},sizes={}):
                        
        G=nx.Graph()
        
        for pair in self.pairs:
            G.add_edge(self.pairs[pair][0],self.pairs[pair][1])
            G.add_edge(self.pairs[pair][0],pair)
            G.add_edge(self.pairs[pair][1],pair)
        
        if probs:
            
            label_changes = copy.deepcopy(labels)
            color_changes = copy.deepcopy(colors)
            size_changes = copy.deepcopy(sizes)
            
            labels = {}
            colors = {}
            sizes = {}
            for node in G:
                if probs[node]>1:
                    labels[node] = ""
                    colors[node] = 'grey'
                    sizes[node] = 3000
                else:
                    labels[node] = "%.0f" % ( 100 * ( probs[node] ) )
                    colors[node] =( 1-probs[node],0,probs[node] )
                    if type(node)!=str:
                        if labels[node]=='0':
                            sizes[node] = 3000
                        else:
                            sizes[node] = 4000 
                    else:
                        if labels[node]=='0':
                            sizes[node] = 800
                        else:
                            sizes[node] = 1150
                                         
            for node in label_changes:
                labels[node] = label_changes[node]
            for node in color_changes:
                colors[node] = color_changes[node]      
            for node in size_changes:
                sizes[node] = size_changes[node]                   
                                        
        else:
            if not labels:
                labels = {}
                for node in G:
                    labels[node] = node
            if not colors:
                colors = {}
                for node in G:
                    if type(node) is int:
                        colors[node] = (node/self.num,0,1-node/self.num)
                    else:
                        colors[node] = (0,0,0)
            if not sizes:
                sizes = {}
                for node in G:
                    if type(node)!=str:
                        sizes[node] = 3000
                    else:
                        sizes[node] = 750

        # convert to lists, which is required by nx
        color_list = []
        size_list = []
        for node in G:
            color_list.append(colors[node])
            size_list.append(sizes[node])
        
        area = [0,0]
        for coord in self.pos.values():
            for j in range(2):
                area[j] = max(area[j],coord[j])
        for j in range(2):
            area[j] = (area[j] + 1 )*1.1
            
        if area[0]>2*area[1]:
            ratio = 0.65
        else:
            ratio = 1

        plt.figure(2,figsize=(2*area[0],2*ratio*area[1])) 
        nx.draw(G, self.pos, node_color = color_list, node_size = size_list, labels = labels, with_labels = True,
                font_color ='w', font_size = 18)
        plt.show() 
        










class walker:
    """Work in progress"""
    def __init__(self,length,device,start=None,samples=1,backend='local_qasm_simulator',shots=1024,method='run'):
        
        self.length = length
        self.start = start
        self.samples = samples
        self.backend = backend
        self.shots = shots
        self.method = method
        
        # device can be a string specifying a device or a tuble specifying a grid
        if isinstance( device, str ):
            backend = get_backend(device)
            self.num = backend.configuration['n_qubits']
            coupling_array = backend.configuration['coupling_map']
            self.coupling = {}
            for n in range(self.num):
                self.coupling[n] = []
            for pair in coupling_array:
                for j in range(2):
                    self.coupling[pair[j]].append(pair[(j+1)%2])
                    self.coupling[pair[(j+1)%2]].append(pair[j])
        else:
            Lx = device[0]
            Ly = device[1]
            self.num = Lx*Ly
            self.coupling = {}
            for n in range(self.num):
                self.coupling[n] = []
            for x in range(Lx-1):
                for y in range(Ly):
                    n = x + y*Ly
                    m = n+1
                    self.coupling[n].append(m)
                    self.coupling[m].append(n)
            for x in range(Lx):
                for y in range(Ly-1):
                    n = x + y*Ly
                    m = n+Ly
                    self.coupling[n].append(m)
                    self.coupling[m].append(n)
         
        if method=='run':
            self.starts, self.walks = self.setup_walks()
        else:
            self.walks = None
        
        self.starts,self.stats = self.get_data()
        
            
    def setup_walks(self):
        
        walks = []
        starts = []
        for sample in range(self.samples):
            
            if not self.start:
                start = random.choice( range(self.num) )
            else:
                start = self.start
            starts.append(start)
            
            walk = [start]
            for l in range(self.length):
                neighbours = list( set(self.coupling[walk[-1]]) - set(walk) )
                if neighbours:
                    walk.append( random.choice( neighbours ) )
                else:
                    walk.append( random.choice( self.coupling[ walk[-1] ] ) )
            walks.append(walk)
            
        return starts, walks
    
    
    def get_data(self):
        
        if self.method=='run':
            batch = []
            for sample in range(self.samples):
                for steps in range(1,self.length+1):

                    qr = QuantumRegister(self.num)
                    cr = ClassicalRegister(self.num)
                    qc = QuantumCircuit(qr,cr)
                    
                    qc.h(qr[self.walks[sample][0]])

                    for step in range(1,steps):
                        n = self.walks[sample][step-1]
                        m = self.walks[sample][step]
                        qc.cx(qr[n],qr[m])
                        qc.h(qr[m])

                    qc.barrier(qr)
                    qc.measure(qr,cr)
                
                    batch.append(qc)
                    
            job = execute(batch, backend=get_backend(self.backend), shots=self.shots)
            
            probs = []
            j = 0
            for sample in range(self.samples):
                probs_for_sample = []
                for step in range(self.length):
                    stats = job.result().get_counts(batch[j])
                    prob = [0]*self.num
                    for string in stats:
                        for n in range(self.num):
                            if string[n]=='1':
                                prob[n] += stats[string]/self.shots
                    probs_for_sample.append( prob )
                    j += 1
                probs.append(probs_for_sample)
               
            starts = self.starts
            
            saveFile = open('results.txt', 'w')
            saveFile.write( str(probs) )
            saveFile.write( str(starts) )
            saveFile.close()
        
        else:
            
            saveFile = open('results.txt')
            saved_data = saveFile.readlines()
            saveFile.close()
            
            probs_string = saved_data[0]
            starts_string = saved_data[1]
            probs = eval(probs_string)
            starts = eval(starts_string)
            
        return starts,probs 