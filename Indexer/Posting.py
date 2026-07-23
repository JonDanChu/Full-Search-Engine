import math

class Document():
    # -----------------------------------------------
    # To be stored in a Postings doc_list as a document that a token is found in.
    #  
    # The member variables are as follows:
    #
    #   docID = The integer that corresponds to a url
    #   df = document frequnecy, The number of occurances of the token on the page
    #   word_position = A list of indexes in the document the token is located at
    #   important_position = A list of the indexes that more important formatting takes place
    #         more specifically for bold, headings (h1, h2, h3), and titles
    # 
    # -----------------------------------------------

    def __init__(self, id: int, wordPosition: int = None, importanceValue: int = 1):
        self.docID = id
        self.tf = 1
        self.word_position = [wordPosition]
        self.importance = importanceValue
    
    def __lt__(self, other):
        return self.docID < other.docID
    
    def add_position(self, pos: int):
        self.tf += 1
        self.word_position.append(pos)
        return

    def export(self):
        return {
            "docID" : self.docID,
            "tf" : self.tf,
            "wordPosition" : self.word_position, 
            "importance" : self.importance}
   
class Posting():
    # -----------------------------------------------
    # To be stored in a list as the value in a dictonary where the key is a token.
    #  
    # The member variables are as follows:
    #   
    #   tf = term frequency, The number of documents stored in the doc_list
    #           ! Important !
    #           Can't be fully determined till after combination of indexes
    #           Not to be used for final score calculation! Use function to get log
    #   doc_list = list of Document objects, the webpages that the given token is found in
    # 
    # -----------------------------------------------

    def __init__(self, freq: int, newDoc: int, pos: int, imp: int):
        self.df = freq
        self.doc_dict = {newDoc: Document(id = newDoc, wordPosition = pos, importanceValue = imp)}

    def get_tf(self, doc: int):
        # returns the weighted version
        return 1 + math.log10(self.doc_dict[doc].tf)
    
    def get_docs(self):
        doc_list = sorted(self.doc_dict.values())
        
    def add_position(self, docID: int, pos: int):
        # Also increases df!!
        if docID not in self.doc_dict:
            self.df += 1
            self.doc_dict[docID] = Document(id = docID, wordPosition = pos)
            return
        
        self.doc_dict[docID].add_position(pos)
        return
    
    def export(self):
        return {
            "df": self.df,
            "docDict": 
                {
                    docID: docInfo.export()
                    for docID, docInfo in sorted(self.doc_dict.items())
                }
        }