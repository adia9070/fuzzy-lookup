import re
import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz
from itertools import combinations
from scipy.sparse import csr_matrix
import sparse_dot_topn.sparse_dot_topn as ct
from sklearn.feature_extraction.text import TfidfVectorizer

def tfidf(df1, df2, index_column_one, index_column_two, fuzzycol1, fuzzycol2, threshold_value, filecheck):
	dict_employee = list()
	passing_employee = list()
	employee_orderid = df1[index_column_one].tolist()
	employee_names = df1[fuzzycol1].tolist()
	df3 = pd.DataFrame({"1":employee_orderid,
						"2":employee_names})
	df3.dropna(inplace=True)
	employee_orderid = df3["1"].tolist()
	employee_names = df3["2"].tolist()
	for name, orderId in zip(employee_names, employee_orderid):
	        original = name
	        name = fuzz._process_and_sort(name,True,True)
	        name = name.replace("  "," ")
	        if 'co' in name.split():
	            name = name.replace('co','company')
	        if 'ltd' in name.split():
	            name = name.replace('ltd','limited')
	        if 'pte' in name.split():
	            name = name.replace('pte','private')
	        if 'corp' in name.split():
	            name = name.replace('corp','corporation')
	        if 'pvt' in name.split():
	            name = name.replace('pvt','private')
	        if 'lt' in name.split():
	            name = name.replace('lt','limited')
	        passing_employee.append(name)
	        dict_employee.append({"processed":name, "original":original, "orderId":orderId})

	dict_vendor = list()
	passing_vendor = list()
	vendor_orderid = df2[index_column_two].tolist()
	vendor_names = df2[fuzzycol2].tolist()
	df3 = pd.DataFrame({"1":vendor_orderid,
						"2":vendor_names})
	df3.dropna(inplace=True)
	vendor_orderid = df3["1"].tolist()
	vendor_names = df3["2"].tolist()
	for name,orderId in zip(vendor_names, vendor_orderid):
	        original = name
	        name = fuzz._process_and_sort(name,True,True)
	        name = name.replace("  "," ")
	        if 'mr' in name.split():
	        	name = name.replace("mr","")
	        if 'co' in name.split():
	            name = name.replace('co','company')
	        if 'ltd' in name.split():
	            name = name.replace('ltd','limited')
	        if 'pte' in name.split():
	            name = name.replace('pte','private')
	        if 'corp' in name.split():
	            name = name.replace('corp','corporation')
	        if 'pvt' in name.split():
	            name = name.replace('pvt','private')
	        if 'lt' in name.split():
	            name = name.replace('lt','limited')
	        passing_vendor.append(name)
	        dict_vendor.append({"processed":name, "original":original, "orderId":orderId})



	def ngrams(string, n=3):
		string = re.sub(r'[,-./]|\sBD',r'', string)
		ngrams = zip(*[string[i:] for i in range(n)])
		return [''.join(ngram) for ngram in ngrams]
	    
	def awesome_cossim_top(A, B, ntop, threshold):
	        A = A.tocsr()
	        B = B.tocsr()
	        M, _ = A.shape
	        _, N = B.shape
	     
	        idx_dtype = np.int32
	     
	        nnz_max = M*ntop
	        indptr = np.zeros(M+1, dtype=idx_dtype)
	        indices = np.zeros(nnz_max, dtype=idx_dtype)
	        data = np.zeros(nnz_max, dtype=A.dtype)

	        ct.sparse_dot_topn(
	            M, N, np.asarray(A.indptr, dtype=idx_dtype),
	            np.asarray(A.indices, dtype=idx_dtype),
	            A.data,
	            np.asarray(B.indptr, dtype=idx_dtype),
	            np.asarray(B.indices, dtype=idx_dtype),
	            B.data,
	            ntop,
	            threshold,
	            indptr, indices, data)

	        return csr_matrix((data,indices,indptr),shape=(M,N))
	
	def return_match_pair(match,name_vector,dict_vendor,limit):
		non_zero = match.nonzero()
		sparse_rows = non_zero[0]
		sparse_columns = non_zero[1]
		key1 = list()
		key2 = list()
		score = list()
		for i, j in zip(sparse_rows, sparse_columns):
			if i == limit:
				break
			score_array = match[i,:].toarray()
			key1.append(name_vector[i]['orderId'])
			key2.append(dict_vendor[j]['orderId'])
			score.append(int(score_array[0][j]*100))
		    
		dataframe = pd.DataFrame({
		    "Refernce_id_one":key1,
		    "Refernce_id_two":key2,
		    "similarity_score":score,
		})
		return dataframe
	
	names = passing_employee + passing_vendor
	passing = dict_employee + dict_vendor
	vectorizer = TfidfVectorizer(min_df = 0,token_pattern='(?u)\\b\\w+\\b')
	tf_idf_matrix = vectorizer.fit_transform(names)
	query = vectorizer.transform(passing_vendor)
	matches = awesome_cossim_top(tf_idf_matrix, query.transpose(), 10, float(threshold_value/100))
	matches_df = return_match_pair(matches, passing, dict_vendor, len(dict_employee))

	if filecheck == "True":
		matches_df = matches_df[matches_df.Refernce_id_one != matches_df.Refernce_id_two]
		matches_df = matches_df[~matches_df[['Refernce_id_one', 'Refernce_id_two']].apply(frozenset, axis=1).duplicated()]
		matches_df = matches_df.reset_index(drop=True)
	
	return matches_df

def send_tfidf_complete_information(dataframe1, dataframe2, tfidf_result, index_column1, index_column2, fuzzycol1, fuzzycol2):
	complete_information = list()

	tfidf_column_header = tfidf_result.columns.values.tolist()
	dataframe1_column_header = dataframe1.columns.values.tolist()
	dataframe2_column_header = dataframe2.columns.values.tolist()

	reference_id1 = tfidf_result["Refernce_id_one"].tolist()
	reference_id2 = tfidf_result["Refernce_id_two"].tolist()

	d1d = dataframe1.groupby(by=index_column1).apply(lambda x: x.index.tolist()).to_dict()
	d2d = dataframe2.groupby(by=index_column2).apply(lambda x: x.index.tolist()).to_dict()
	d3d = tfidf_result.groupby(by=["Refernce_id_one","Refernce_id_two"]).apply(lambda x: x.index.tolist()).to_dict()

	for rid1, rid2 in zip(reference_id1, reference_id2):
		tf_val = tfidf_result.iloc[d3d[(rid1,rid2)]].values.tolist()[0]
		df1_val = dataframe1.iloc[d1d[rid1]][fuzzycol1].values.tolist()
		df2_val = dataframe2.iloc[d2d[rid2]][fuzzycol2].values.tolist()
		
		info = [tf_val[0]] + df1_val + [tf_val[1]] + df2_val + [tf_val[2]]
		complete_information.append(info)

	complete_header = ['Refernce_id_one(index)', fuzzycol1, 'Refernce_id_two(index)', fuzzycol2, 'similarity_score']
	complete_result = pd.DataFrame(complete_information, columns=complete_header)

	return complete_result