//
//  test.cpp
//  MLMPME
//
//  Created by 曹艺馨 on 17/4/3.
//  Copyright © 2017年 ethan. All rights reserved.
//

#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    int nrows = 3;
    int ncolumns = 2,i;
    int **array1 = (int **)malloc(nrows * sizeof(int *));
    for(i = 0; i < nrows; i++)
        array1[i] = (int *)malloc(ncolumns * sizeof(int));
    
}
