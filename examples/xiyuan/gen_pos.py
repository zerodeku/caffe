#!/usr/bin/python
import os
import shutil
import time
import cv2

import tarfile
import re
import sqlite3

from utils import (need_tmp_dir, display_imgs_in_tar)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

input_dir = os.path.join(CURRENT_DIR, '../../data/xiyuan')
output_dir = os.path.join(CURRENT_DIR, '../../data/xiyuan')
tmp_dir = '/tmp/aflw'
res_prefix = 'aflw/data/flickr'

tar_in_files = ['aflw-images-3.tar.gz', 'aflw-images-2.tar.gz', 'aflw-images-0.tar.gz']
tar_out_file = 'pos.tar.gz'

SELECT_FACE_ID_FROM_FILE_ID = "select face_id from Faces where file_id='%s'"
SELECT_FACE_RECT_FROM_ID = "select x, y, w, h from FaceRect where face_id='%s'"

# every cropped face is 30 by 30
W, H = 30, 30
angles = xrange(-40, 50, 10)


@need_tmp_dir(tmp_dir)
def main():
    for _tar in tar_in_files:
        tar_idx = int(re.match('.*-(\d*)\..*', _tar).group(1))
        tic = time.time()
        count = 0
        with tarfile.open(os.path.join(input_dir, _tar)) as tar_in:
            while True:
                ti = tar_in.next()
                if not ti:
                    break

                # get file_id
                file_id = None
                try:
                    m = re.match('.*/(.*\.jpg)', ti.name)
                    file_id = m.group(1)
                except IndexError, e:
                    continue
                except AttributeError, e:
                    continue
                if file_id is None:
                    continue

                # extract to /tmp and read image
                tar_in.extract(ti, tmp_dir)
                img_file = os.path.join(tmp_dir, res_prefix, str(tar_idx), file_id)
                img = cv2.imread(img_file)

                # get face_id
                cursor.execute(SELECT_FACE_ID_FROM_FILE_ID % file_id)
                face_id = cursor.fetchone()
                if face_id is None:
                    continue
                face_id = face_id[0]

                # TODO: delete debug
                # if face_id != 55354:
                #     continue

                # get face rect
                cursor.execute(SELECT_FACE_RECT_FROM_ID % face_id)
                rect = cursor.fetchone()
                if rect is None:
                    continue
                x, y, w, h = rect

                # add padding if necessary
                if x < 0 or y < 0 or\
                        x+w > img.shape[1] or\
                        y+h > img.shape[0]:
                    img = cv2.copyMakeBorder(img,
                                             -min(0, y),
                                             max(0, y+h-img.shape[0]),
                                             -min(0, x),
                                             max(0, x+w-img.shape[1]),
                                             cv2.BORDER_CONSTANT)
                    x = max(0, x)
                    y = max(0, y)

                # only now, we make sure the image is valid
                count += 1
                if count % 1000 == 0:
                    toc = time.time()
                    print 'tar_idx, count, time = %d, %d, %d' % (tar_idx, count, toc-tic)
                    tic = time.time()

                # patch faces with rotations
                img_out_file = os.path.join(tmp_dir, 'tmp.jpg')
                for angle in angles:
                    r = cv2.getRotationMatrix2D((x+w/2, y+h/2), angle, 1.0)
                    img_rot = cv2.warpAffine(img, r, (img.shape[1], img.shape[0]))
                    face = img_rot[y:y+h, x:x+w, :]

                    # TODO: delete debug
                    # cv2.imshow("img", img)
                    # cv2.imshow("img_rot", img_rot)
                    # print x, y, x+w, y+h
                    # print img.shape
                    # print img_rot.shape
                    # #cv2.imshow("face", face)
                    # raw_input("Press Enter to continue...")
                    # exit()

                    face = cv2.resize(face, (W, H))
                    cv2.imwrite(img_out_file, face)
                    tar_out.add(img_out_file, '%06d_%d.jpg' % (face_id, angle))

                # clean up
                os.remove(img_file)
                os.remove(img_out_file)
    shutil.rmtree(tmp_dir)


def show():
    display_imgs_in_tar(os.path.join(output_dir, tar_out_file))


if __name__ == '__main__':
    tar_out = tarfile.open(os.path.join(output_dir, tar_out_file), 'w')
    sqlfile = os.path.join(input_dir, 'aflw.sqlite')
    conn = sqlite3.connect(sqlfile)
    cursor = conn.cursor()

    main()

    conn.close()
    tar_out.close()