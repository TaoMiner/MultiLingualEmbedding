//
//  main.cpp
//  test
//
//  Created by 曹艺馨 on 17/4/3.
//  Copyright © 2017年 ethan. All rights reserved.
//

#include <stdio.h>
#include <stdlib.h>

void set(int x[2][3]){
    int i,j;
    for(i = 0; i < 2; i++)
        for (j=0;j<3;j++)
            x[i][j] += 1;
}

int main(int argc, const char * argv[]) {
    int i,j;
    int array1[2][3];
    for(i = 0; i < 2; i++)
        for (j=0;j<3;j++)
            array1[i][j] = i+j;
    for(i = 0; i < 2; i++)
        for (j=0;j<3;j++)
            printf("%d", array1[i][j]);
    printf("\n");
    set(array1);
    for(i = 0; i < 2; i++)
        for (j=0;j<3;j++)
            printf("%d", array1[i][j]);
}
