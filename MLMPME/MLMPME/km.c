//
//  mlmpme.cpp
//  MLMPME
//
//  Created by  on 17/3/16.
//  Copyright © 2017年 ethan. All rights reserved.
//

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>


#define inf 1000000000
#define _clr(x, len) memset(x,-1,sizeof(int)*len)

#define MAX_SENTENCE_LENGTH 1000
#define MAX_PAR_SENT 10

struct KM_var {
    int m,n;
    float *matrix;
    int match1[MAX_PAR_SENT*MAX_SENTENCE_LENGTH], match2[MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
    int s[MAX_PAR_SENT*MAX_SENTENCE_LENGTH], t[MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
    float l1[MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
    float l2[MAX_PAR_SENT*MAX_SENTENCE_LENGTH];
};

bool isequal(float a,float b)
{
    if(fabs(a-b)<0.000001)
        return 1;
    return 0;
}

float km_match(struct KM_var *km_var)
{
    for (int i=0;i<km_var->m;i++){
        for (int j=0;j<km_var->n;j++){
            km_var->matrix[i*km_var->n + j] = i*km_var->n + j;
            printf("%d,",i*km_var->n + j);
        }
        printf("\n");
    }
    int p,q,i,j,k;
    int m = km_var->m;
    int n = km_var->n;
    float res=0;
    int *s = km_var->s;
    int *t = km_var->t;
    float *l1 = km_var->l1;
    float *l2 = km_var->l2;
    for(i=0;i<m;i++)
    {
        l1[i]=-10000000;
        
        for(j=0;j<n;j++)
            l1[i]=km_var->matrix[i*n+j]>l1[i]?km_var->matrix[i*n+j]:l1[i];
        if(isequal(l1[i],-10000000))
            return -1;
    }
    
    for(i=0;i<n;i++)
        l2[i]=0;
    _clr(km_var->match1, MAX_PAR_SENT*MAX_SENTENCE_LENGTH);
    _clr(km_var->match2, MAX_PAR_SENT*MAX_SENTENCE_LENGTH);
    for(i=0;i<m;i++)
    {
        _clr(t, MAX_PAR_SENT*MAX_SENTENCE_LENGTH);
        p=0;q=0;
        for(s[0]=i;p<=q&&km_var->match1[i]<0;p++)
        {
            for(k=s[p],j=0;j<n&&km_var->match1[i]<0;j++)
            {
                if(isequal(l1[k]+l2[j],km_var->matrix[k*n+j])&&t[j]<0)
                {
                    s[++q]=km_var->match2[j];
                    t[j]=k;
                    if(s[q]<0)
                    {
                        for(p=j;p>=0;j=p)
                        {
                            km_var->match2[j]=k=t[j];
                            p=km_var->match1[k];
                            km_var->match1[k]=j;
                        }
                    }
                }
            }
        }
        
        if(km_var->match1[i]<0)
        {
            i--;
            float pp=10000000;
            for(k=0;k<=q;k++)
            {
                for(j=0;j<n;j++)
                {
                    if(t[j]<0&&l1[s[k]]+l2[j]-km_var->matrix[s[k]*n+j]<pp)
                        pp=l1[s[k]]+l2[j]-km_var->matrix[s[k]*n+j];
                }
            }
            for(j=0;j<n;j++)
                l2[j]+=t[j]<0?0:pp;
            for(k=0;k<=q;k++)
                l1[s[k]]-=pp;
        }
    }
    for(i=0;i<m;i++)
        res+=km_var->matrix[i*n+km_var->match1[i]];
    for (int i=0;i<km_var->m;i++)
        printf("%d--%d:%f\n",i,km_var->match1[i], km_var->matrix[i*km_var->n+km_var->match1[i]]);
    printf("res:%f\n",res);
    return res;
}

/*
int main(int argc, char **argv) {
    struct KM_var km_var;
    float res;
    km_var.m = 2;
    km_var.n = 3;
    km_var.matrix = (float *)calloc(km_var.m * km_var.n, sizeof(float));
    for (int i=0;i<km_var.m;i++){
        for (int j=0;j<km_var.n;j++){
            km_var.matrix[i*km_var.n + j] = i*km_var.n + j;
            printf("%d,",i*km_var.n + j);
        }
        printf("\n");
    }
    res = km_match(&km_var);
    for (int i=0;i<km_var.m;i++)
        printf("%d--%d:%f\n",i,km_var.match1[i], km_var.matrix[i*km_var.n+km_var.match1[i]]);
}
*/














