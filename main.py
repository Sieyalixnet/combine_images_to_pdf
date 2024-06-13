from functools import partial
from multiprocessing import Pool
import os
import time
from typing import List, Tuple
import zipfile
import rarfile
import shutil
import img2pdf
from PIL import Image
import pillow_avif #Do NOT remove this
import PyPDF2
import uuid
import argparse
import sys

BOOKS = []
EXISTED_PATH = []#becasue when multi-processing, the file may not saved to OUTPUTDIR, so there it may be use the same path.
OUTPUTDIR = 'output'
TARGETDIR = "__target" 
FAILED = []

def remove_transparency(im, bg_colour=(255, 255, 255)):
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
        alpha = im.convert('RGBA').split()[-1]
        bg = Image.new("RGBA", im.size, bg_colour + (255,))
        bg.paste(im, mask=alpha)
        return bg
    else:
        return im

def combine_pdf(img_paths:List[str],output_filename:str,output_dir:str,fullpath:str,UUID:str):
    global TARGETDIR,EXISTED_PATH,OUTPUTDIR,FAILED
    '''
    combine the image paths to a PDF file.
    '''
    pdf_merger = PyPDF2.PdfMerger()
    for (index, img_path) in enumerate(img_paths):
        image = remove_transparency(Image.open(img_path))
        #Invalid rotate value will be judged 
        rotated = False
        img_exif = image.getexif()
        img_exif.items()
        if img_exif is not None:
            for key, val in img_exif.items():
                if key == 0x0112:
                    rotated=True
                    break
        if rotated==False:
            pdf_bytes = img2pdf.convert(image.filename)
        else:
            pdf_bytes = img2pdf.convert(image.filename,rotation=img2pdf.Rotation.ifvalid)
        file = open(f"./avif_temp_pdf_{UUID}.pdf", "wb")
        file.write(pdf_bytes)
        try:
            pdf_merger.append(PyPDF2.PdfReader(f"./avif_temp_pdf_{UUID}.pdf", strict=False))
        except Exception as e:
            err = f"can not combine page {index} of {output_filename} because {e}"
            FAILED.append(err)
            print(err)
        image.close()
        file.close()
        if os.path.exists(img_path):
            os.remove(img_path)
    destination:List[str] = fullpath.replace(f"./{TARGETDIR}","").split("\\")
    zipfilename = None
    if destination.__len__()>=2:
        zipfilename = destination[-2]
        if os.path.exists("./"+OUTPUTDIR+"/"+zipfilename) is False:
            os.makedirs("./"+OUTPUTDIR+"/"+zipfilename)
        path = "./"+OUTPUTDIR+"/"+zipfilename+"/"+output_filename+"$$"+(uuid.uuid4()).__str__().replace("-","",-1)+".pdf"
        print(path)
    #To ensure that name is unique. The name will be edited to origin name if it is possible in `rename()`
    else:
        path = "./"+output_dir+"/"+output_filename+"$$"+(uuid.uuid4()).__str__().replace("-","",-1)+".pdf"
    print("combine to pdf:",path)
    pdf_merger.write(path)
    pdf_merger.close()

def get_file_name(path:str,suffix:List[str],current=False)->Tuple[List[str],List[str]]:
    '''
    Current: `False` including the children files, while `True` only search the recent file of "path"
    Output: (names:`List[str]`,paths:`List[str]`)
    '''
    input_template_All=[]
    input_template_All_Path=[]
    if current == False:
        for root, dirs, files in os.walk(path, topdown=True):
            for name in files:
                if os.path.splitext(name)[1] in suffix:
                    input_template_All.append(name)
                    input_template_All_Path.append(os.path.join(root, name))
        return input_template_All,input_template_All_Path
    elif current == True:
        fileList = os.listdir(path)
        for name in fileList:
            if os.path.splitext(name)[1] in suffix:
                input_template_All.append(name)
                input_template_All_Path.append(os.path.join(path, name))
        return (input_template_All,input_template_All_Path)
    else:
        assert False, "Current must be refer"

def extract_zip(zip_file, extract_path):
    '''
    extract zip file to a path
    '''
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

def extract_rar(rar_file, extract_path):
    '''
    extract rar file to a path
    '''
    with rarfile.RarFile(rar_file, 'r') as rar_ref:
        rar_ref.extractall(extract_path)

def _extract(base_dir,iter):
    '''
    get all zip files in __temp and extract them into {TARGETDIR}
    '''
    (root, dirs, files) = iter
    for file in files:
        file_path = os.path.join(root, file)
        if file.endswith('.zip') or file.endswith('.cbz') or file.endswith('.rar'):
            print("extracting:",file_path)
            files_names:List[str] = file.split(".")
            if files_names.__len__()<=2:
                path = f"./{TARGETDIR}/"+file.split(".")[0].replace(".","")
            else:
                max_length_name = None
                for _name in files_names:
                    if max_length_name is None or _name.__len__()>max_length_name.__len__():
                        max_length_name = _name
                path = f"./{TARGETDIR}/"+max_length_name.replace(".","")
            path = path.strip()
            if os.path.exists(path)==False:
                try:
                    os.makedirs(path)
                except Exception as e:
                    print("can not mkdirs: ",path, " becasue :",e)
            if file.endswith('.zip') or file.endswith('.cbz') :
                extract_zip(file_path, path)
            elif file.endswith('.rar'):
                extract_rar(file_path, path)
        if base_dir=="./__temp":
            os.remove(file_path)

def extract_recursive(base_dir):
    '''
    extract all the file in __temp to __target
    '''
    _targets = list(os.walk(base_dir))
    targets=[]
    for item in _targets:#get all the ZIP or RAR or CBZ file
        if len(item[2])>0:
            for f in item[2]:
                if f.endswith(".cbz") or f.endswith(".zip") or f.endswith(".rar"):
                    targets.append((item[0],item[1],[f]))
    with Pool() as pool:
        results = pool.map(partial(_extract,base_dir),targets)
        pool.close() 
        pool.join()

def move_all_zipped_files():
    '''
    Some zip files may contains children zip files.\n
    So move all children zip files in {TARGETDIR} to __temp\n
    If there is NOT any zip/cbz/rar files in {TARGETDIR} it will return True.
    '''
    allclear = True
    for root, dirs, files in os.walk(f"./{TARGETDIR}"):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if file.endswith('.zip'):
                    shutil.move(file_path,"./__temp")
                    allclear=False
                elif file.endswith('.rar'):
                    shutil.move(file_path,"./__temp")
                    allclear=False
                elif file.endswith('.cbz'):
                    shutil.move(file_path,"./__temp")
                    allclear=False
            except Exception as e:
                os.remove(file_path)
                print("error:",e,"removed")
    return allclear

def join_into_books():
    '''
    find all images in {TARGETDIR} and append it into BOOKS, the task queue.
    '''
    global BOOKS
    allclear = True
    for root, dirs, files in os.walk(f"./{TARGETDIR}"):
        recentdir = None
        if root.split("\\")[-1] == recentdir:
            continue
        for file in files:
            file_path = os.path.join(root, file)
            lower_file_name = file.lower()
            if lower_file_name.endswith(".jpg") or lower_file_name.endswith(".jpeg") or lower_file_name.endswith(".png") or lower_file_name.endswith(".avif") or lower_file_name.endswith(".bmp") :
                sfx =   "."+ file.split(".")[-1]
                tmp = {"path":root,"suffix":[sfx],"name":root.split("\\")[-1]}
                has = False
                for book in BOOKS:#BOOKS has this book name
                    if book.get("path") == root:
                        has=True
                        if sfx not in book.get("suffix"):
                            book.get("suffix").append(sfx)
                if has == False:
                    BOOKS.append(tmp)
                    recentdir = root.split("\\")[-1]
                    # break
    return allclear

def _trans_avif_to_png(item):
    if ".avif" in item.get("suffix") or ".AVIF" in item.get("suffix"):
        images = get_file_name(item.get("path"),item.get("suffix"),True)
        print(f"file avif{item.get('name')} to png")
        for img in images[1]:#img is a path
            imga = Image.open(img)
            imga.save(item.get("path")+"\\"+(img.split("\\"))[-1].split(".")[-2]+".png","png")
        if ".avif" in item["suffix"]:
            item["suffix"].remove(".avif")
        if ".AVIF" in item["suffix"]:
            item["suffix"].remove(".AVIF")
        if ".png" not in item["suffix"]:
            item["suffix"].append(".png")
        

def try_trans_avif_to_png():
    global BOOKS
    with Pool() as pool:
        results = pool.map(_trans_avif_to_png,BOOKS)
        pool.close()  # No more tasks can be submitted
        pool.join() 

            
def clear_exist():
    global OUTPUTDIR,TARGETDIR
    mk_clear_dir(TARGETDIR)
    mk_clear_dir("__temp")
    mk_clear_dir(OUTPUTDIR)
        
def mk_clear_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.mkdir(path)

def copy_pictures(base_dir):
    suffix = [".avif",".jpg",".jpeg",".bmp",".png"]
    for s in suffix:
        copy_file_to_target(s,base_dir)
         
def copy_file_to_target(suffix,base_dir):
    images = get_file_name(base_dir,[suffix],False)
    copied = []
    for item in images[1]:
        # print(item)
        if item.split("\\")[-2] not in copied:
            shutil.copytree("\\".join(item.split("\\")[:-1]),f"./{TARGETDIR}/"+item.split("\\")[-2],dirs_exist_ok=True)
            print(f"copy {suffix} to target:",item.split("\\")[-2])
            copied.append(item.split("\\")[-2])

def copy_file_to_output(suffix,base_dir):
    global OUTPUTDIR
    files = get_file_name(base_dir,[suffix],False)
    for i in range(len(files[1])):
        print(f"copy {suffix} to output:", files[0][i])
        item= files[1][i]
        shutil.copy(item,f"./{OUTPUTDIR}/f{files[0][i]}")

def _combine(item):
    global OUTPUTDIR
    print("combining books to pdf:",item.get("name"))
    _ID = uuid.uuid4()
    try:
        images = get_file_name(item.get("path"),item.get("suffix"),True)
        combine_pdf(images[1],item.get("name"),OUTPUTDIR,item.get("path"),_ID)
        # shutil.rmtree(item.get("path"))
        print("removed extracted files: ",item.get("path"))
    except Exception as e:
        err = f"error while combing:{item.get('name')} because {e}"
        print(err)
    if os.path.exists(f"avif_temp_pdf_{_ID}.pdf"):
            os.remove(f"./avif_temp_pdf_{_ID}.pdf")

def combine():
    global BOOKS,OUTPUTDIR,FAILED
    with Pool() as pool:
        results = pool.map(_combine,BOOKS)
        pool.close()  # No more tasks can be submitted
        pool.join()   
        
def rename():
    global OUTPUTDIR
    pdfs = get_file_name(f"./{OUTPUTDIR}",[".pdf"],False)
    for item in pdfs[1]:
        item:str = item
        splited_name = item.split("$$")
        target_name = splited_name[0]+".pdf"
        now_digit= 1
        while os.path.exists(target_name)==True:
            target_name = splited_name[0]+ splited_name[1][:now_digit] +".pdf"
            now_digit+=1
            if now_digit>=15:
                break
        if os.path.exists(target_name)==False:
            shutil.move(item,target_name)
            print("rename:",item,target_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p','--path',type=str,default=sys.path[0],help='Base path of processing. Default: recent path')
    parser.add_argument('--no_copy',action='store_true',default=False,help='Do not copy existed pdf/epub/pictures from base path.')
    parser.add_argument('--no_clear',action='store_true',default=False,help='Do not remove the existed files of temp dir, target dir and output dir.')
    opt = parser.parse_args()
    time0 = time.time()
    base_directory = opt.path
    print('The path will be processing:', base_directory)
    print('The output Dir:',OUTPUTDIR)
    if opt.no_clear is False:
        clear_exist()
    if opt.no_copy is False:
        copy_file_to_output(".pdf",base_directory)
        copy_file_to_output(".epub",base_directory)
        copy_pictures(base_directory)
    extract_recursive(base_directory)
    while move_all_zipped_files()==False:
        extract_recursive("./__temp")
    print("extracted all files")
    join_into_books()   
    combine()
    rename()
    mk_clear_dir(TARGETDIR)
    print(f'finished in {time.time()-time0}')
    
