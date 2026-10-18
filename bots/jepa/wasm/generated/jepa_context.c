#include <tgmath.h>
#include <stddef.h>

void jepa_context_E_24_37n1(float* restrict data0_888, float* restrict data1_504, int* restrict data2_24, float* restrict data3_1024, float* restrict data4_512, float* restrict data5_976) {
  for (int Lidx3 = 0; Lidx3 < 24; Lidx3++) {
    int val0 = (*(data2_24+Lidx3));
    int alu0 = (val0*7);
    int alu1 = (alu0+3);
    _Bool alu2 = (val0<0);
    int alu3 = (alu2?63:0);
    int alu4 = ((val0+alu3)>>6);
    int alu5 = ((alu2&((val0&63)!=0))?(alu4+-1):alu4);
    int alu6 = (val0+(alu5*-64));
    int alu7 = ((alu1<0)?1:0);
    int alu8 = (((int)(((((long long)(alu1))*1126548799ll)>>36ll)))+alu7);
    int alu9 = (((alu0<-3)&((alu1-(61*alu8))!=0))?(alu8+-1):alu8);
    int alu10 = (alu0+(alu9*-61));
    int alu11 = ((alu6<0)?(alu6+64):alu6);
    int alu12 = ((alu10<-3)?(alu10+64):(alu10+3));
    int alu13 = ((alu5<0)?(alu5+32):alu5);
    for (int Lidx4 = 0; Lidx4 < 37; Lidx4++) {
      _Bool alu14 = (Lidx4<21);
      float val1 = (alu14?*(data1_504+((Lidx3*21)+Lidx4)):0.0f);
      _Bool alu15 = (20<Lidx4);
      float val2 = ((alu15&(-1<alu11)&(alu11<64))?*(data3_1024+((alu11<<4)+Lidx4+-21)):0.0f);
      float val3 = ((alu15&(-1<alu13)&(alu13<32))?*(data4_512+((alu13<<4)+Lidx4+-21)):0.0f);
      float val4 = ((alu15&(-1<alu12)&(alu12<61))?*(data5_976+((alu12<<4)+Lidx4+-21)):0.0f);
      float alu16 = (alu14?0.0f:(val2+val3+val4));
      *(data0_888+((Lidx3*37)+Lidx4)) = (val1+alu16);
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25n1(float* restrict data0_1, float* restrict data1_24) {
  float4 val0 = (*((float4*)((data1_24+0))));
  float4 val1 = (*((float4*)((data1_24+4))));
  float4 val2 = (*((float4*)((data1_24+8))));
  float4 val3 = (*((float4*)((data1_24+12))));
  float4 val4 = (*((float4*)((data1_24+16))));
  float4 val5 = (*((float4*)((data1_24+20))));
  *(data0_1+0) = (val0[0]+val0[1]+val0[2]+val0[3]+val1[0]+val1[1]+val1[2]+val1[3]+val2[0]+val2[1]+val2[2]+val2[3]+val3[0]+val3[1]+val3[2]+val3[3]+val4[0]+val4[1]+val4[2]+val4[3]+val5[0]+val5[1]+val5[2]+val5[3]+1.0f);
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4_73_37n1(float* restrict data0_1600, float* restrict data1_73, float* restrict data2_4672, float* restrict data3_64, float* restrict data4_888, float* restrict data5_2368, float* restrict data6_64) {
  float acc0[4];
  float acc1[4];
  for (int Lidx2 = 0; Lidx2 < 25; Lidx2++) {
    _Bool alu0 = (Lidx2<1);
    for (int Lidx3 = 0; Lidx3 < 16; Lidx3++) {
      int alu1 = (Lidx3<<2);
      *(acc1+0) = 0.0f;
      *(acc1+1) = 0.0f;
      *(acc1+2) = 0.0f;
      *(acc1+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 73; Ridx0++) {
        float val0 = (*(data1_73+Ridx0));
        float4 val1 = (*((float4*)((data2_4672+((Ridx0<<6)+alu1)))));
        *(acc1+0) = ((*(acc1+0))+(val0*val1[0]));
        *(acc1+1) = ((*(acc1+1))+(val0*val1[1]));
        *(acc1+2) = ((*(acc1+2))+(val0*val1[2]));
        *(acc1+3) = ((*(acc1+3))+(val0*val1[3]));
      }
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx1 = 0; Ridx1 < 37; Ridx1++) {
        float val2 = ((0<Lidx2)?*(data4_888+((Lidx2*37)+Ridx1+-37)):0.0f);
        float4 val3 = (*((float4*)((data5_2368+((Ridx1<<6)+alu1)))));
        *(acc0+0) = ((*(acc0+0))+(val2*val3[0]));
        *(acc0+1) = ((*(acc0+1))+(val2*val3[1]));
        *(acc0+2) = ((*(acc0+2))+(val2*val3[2]));
        *(acc0+3) = ((*(acc0+3))+(val2*val3[3]));
      }
      float4 val4 = (*((float4*)((data3_64+alu1))));
      float4 val5 = (*((float4*)((data6_64+alu1))));
      float alu20 = (alu0?((*(acc1+0))+val4[0]):0.0f);
      float alu21 = (alu0?0.0f:((*(acc0+0))+val5[0]));
      float alu22 = (alu0?((*(acc1+1))+val4[1]):0.0f);
      float alu23 = (alu0?0.0f:((*(acc0+1))+val5[1]));
      float alu24 = (alu0?((*(acc1+2))+val4[2]):0.0f);
      float alu25 = (alu0?0.0f:((*(acc0+2))+val5[2]));
      float alu26 = (alu0?((*(acc1+3))+val4[3]):0.0f);
      float alu27 = (alu0?0.0f:((*(acc0+3))+val5[3]));
      *((float4*)((data0_1600+((Lidx2<<6)+alu1)))) = (float4){(alu20+alu21),(alu22+alu23),(alu24+alu25),(alu26+alu27)};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4n2(float* restrict data0_25, float* restrict data1_1600) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
      *(acc0+0) = ((*(acc0+0))+val0[0]+val0[1]+val0[2]+val0[3]);
    }
    *(data0_25+Lidx1) = ((*(acc0+0))*0.015625f);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4n3(float* restrict data0_25, float* restrict data1_1600, float* restrict data2_25) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    float val0 = (*(data2_25+Lidx1));
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val1 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
      float alu1 = (val1[0]-val0);
      float alu2 = (val1[1]-val0);
      float alu3 = (val1[2]-val0);
      float alu4 = (val1[3]-val0);
      *(acc0+0) = ((*(acc0+0))+(alu1*alu1)+(alu2*alu2)+(alu3*alu3)+(alu4*alu4));
    }
    *(data0_25+Lidx1) = (1.0f/__builtin_sqrtf((((*(acc0+0))*0.015625f)+1e-05f)));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_E_25_16_4n1(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_25, float* restrict data3_25, float* restrict data4_64, float* restrict data5_64) {
  for (int Lidx0 = 0; Lidx0 < 25; Lidx0++) {
    float val0 = (*(data2_25+Lidx0));
    float val1 = (*(data3_25+Lidx0));
    for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
      int alu0 = (Lidx1<<2);
      int alu1 = ((Lidx0<<6)+alu0);
      float4 val2 = (*((float4*)((data1_1600+alu1))));
      float4 val3 = (*((float4*)((data4_64+alu0))));
      float4 val4 = (*((float4*)((data5_64+alu0))));
      *((float4*)((data0_1600+alu1))) = (float4){(((val2[0]-val0)*val1*val3[0])+val4[0]),(((val2[1]-val0)*val1*val3[1])+val4[1]),(((val2[2]-val0)*val1*val3[2])+val4[2]),(((val2[3]-val0)*val1*val3[3])+val4[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4_16_4n1(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_4096, float* restrict data3_64) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    int alu0 = (Lidx1<<6);
    for (int Lidx2 = 0; Lidx2 < 16; Lidx2++) {
      int alu1 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
        float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+alu0)))));
        int alu6 = ((Ridx0<<8)+alu1);
        float4 val1 = (*((float4*)((data2_4096+(alu6+64)))));
        float4 val2 = (*((float4*)((data2_4096+(alu6+128)))));
        float4 val3 = (*((float4*)((data2_4096+(alu6+192)))));
        float4 val4 = (*((float4*)((data2_4096+alu6))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val4[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val4[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val4[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val4[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3]));
      }
      float4 val5 = (*((float4*)((data3_64+alu1))));
      *((float4*)((data0_1600+(alu0+alu1)))) = (float4){((*(acc0+0))+val5[0]),((*(acc0+1))+val5[1]),((*(acc0+2))+val5[2]),((*(acc0+3))+val5[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4_16_4n2(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_4096, float* restrict data3_64) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    int alu0 = (Lidx1<<6);
    for (int Lidx2 = 0; Lidx2 < 16; Lidx2++) {
      int alu1 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
        float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+alu0)))));
        int alu6 = ((Ridx0<<8)+alu1);
        float4 val1 = (*((float4*)((data2_4096+(alu6+64)))));
        float4 val2 = (*((float4*)((data2_4096+(alu6+128)))));
        float4 val3 = (*((float4*)((data2_4096+(alu6+192)))));
        float4 val4 = (*((float4*)((data2_4096+alu6))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val4[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val4[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val4[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val4[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3]));
      }
      float4 val5 = (*((float4*)((data3_64+alu1))));
      *((float4*)((data0_1600+(alu0+alu1)))) = (float4){((*(acc0+0))+val5[0]),((*(acc0+1))+val5[1]),((*(acc0+2))+val5[2]),((*(acc0+3))+val5[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4_16_4n3(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_4096, float* restrict data3_64) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    int alu0 = (Lidx1<<6);
    for (int Lidx2 = 0; Lidx2 < 16; Lidx2++) {
      int alu1 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
        float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+alu0)))));
        int alu6 = ((Ridx0<<8)+alu1);
        float4 val1 = (*((float4*)((data2_4096+(alu6+64)))));
        float4 val2 = (*((float4*)((data2_4096+(alu6+128)))));
        float4 val3 = (*((float4*)((data2_4096+(alu6+192)))));
        float4 val4 = (*((float4*)((data2_4096+alu6))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val4[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val4[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val4[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val4[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3]));
      }
      float4 val5 = (*((float4*)((data3_64+alu1))));
      *((float4*)((data0_1600+(alu0+alu1)))) = (float4){((*(acc0+0))+val5[0]),((*(acc0+1))+val5[1]),((*(acc0+2))+val5[2]),((*(acc0+3))+val5[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_25_4_16n1(float* restrict data0_2500, float* restrict data1_1600, float* restrict data2_1600, float* restrict data3_24) {
  for (int Lidx2 = 0; Lidx2 < 25; Lidx2++) {
    int alu0 = (Lidx2<<6);
    float4 val0 = (*((float4*)((data1_1600+(alu0+4)))));
    float4 val1 = (*((float4*)((data1_1600+(alu0+8)))));
    float4 val2 = (*((float4*)((data1_1600+(alu0+12)))));
    float4 val3 = (*((float4*)((data1_1600+(alu0+16)))));
    float4 val4 = (*((float4*)((data1_1600+(alu0+20)))));
    float4 val5 = (*((float4*)((data1_1600+(alu0+24)))));
    float4 val6 = (*((float4*)((data1_1600+(alu0+28)))));
    float4 val7 = (*((float4*)((data1_1600+(alu0+32)))));
    float4 val8 = (*((float4*)((data1_1600+(alu0+36)))));
    float4 val9 = (*((float4*)((data1_1600+(alu0+40)))));
    float4 val10 = (*((float4*)((data1_1600+(alu0+44)))));
    float4 val11 = (*((float4*)((data1_1600+(alu0+48)))));
    float4 val12 = (*((float4*)((data1_1600+(alu0+52)))));
    float4 val13 = (*((float4*)((data1_1600+(alu0+56)))));
    float4 val14 = (*((float4*)((data1_1600+(alu0+60)))));
    float4 val15 = (*((float4*)((data1_1600+alu0))));
    for (int Lidx3 = 0; Lidx3 < 25; Lidx3++) {
      float val16 = ((0<Lidx3)?*(data3_24+(Lidx3+-1)):0.0f);
      int alu1 = (Lidx3<<6);
      float4 val17 = (*((float4*)((data2_1600+(alu1+4)))));
      float4 val18 = (*((float4*)((data2_1600+(alu1+8)))));
      float4 val19 = (*((float4*)((data2_1600+(alu1+12)))));
      float4 val20 = (*((float4*)((data2_1600+(alu1+16)))));
      float4 val21 = (*((float4*)((data2_1600+(alu1+20)))));
      float4 val22 = (*((float4*)((data2_1600+(alu1+24)))));
      float4 val23 = (*((float4*)((data2_1600+(alu1+28)))));
      float4 val24 = (*((float4*)((data2_1600+(alu1+32)))));
      float4 val25 = (*((float4*)((data2_1600+(alu1+36)))));
      float4 val26 = (*((float4*)((data2_1600+(alu1+40)))));
      float4 val27 = (*((float4*)((data2_1600+(alu1+44)))));
      float4 val28 = (*((float4*)((data2_1600+(alu1+48)))));
      float4 val29 = (*((float4*)((data2_1600+(alu1+52)))));
      float4 val30 = (*((float4*)((data2_1600+(alu1+56)))));
      float4 val31 = (*((float4*)((data2_1600+(alu1+60)))));
      float4 val32 = (*((float4*)((data2_1600+alu1))));
      int alu2 = ((Lidx2*25)+Lidx3);
      float alu3 = ((Lidx3<1)?1.0f:val16);
      float alu4 = ((alu3+-1.0f)*1000000000.0f);
      *(data0_2500+(alu2+625)) = ((((val3[0]*val20[0])+(val3[1]*val20[1])+(val3[2]*val20[2])+(val3[3]*val20[3])+(val4[0]*val21[0])+(val4[1]*val21[1])+(val4[2]*val21[2])+(val4[3]*val21[3])+(val5[0]*val22[0])+(val5[1]*val22[1])+(val5[2]*val22[2])+(val5[3]*val22[3])+(val6[0]*val23[0])+(val6[1]*val23[1])+(val6[2]*val23[2])+(val6[3]*val23[3]))*0.25f)+alu4);
      *(data0_2500+(alu2+1250)) = ((((val7[0]*val24[0])+(val7[1]*val24[1])+(val7[2]*val24[2])+(val7[3]*val24[3])+(val8[0]*val25[0])+(val8[1]*val25[1])+(val8[2]*val25[2])+(val8[3]*val25[3])+(val9[0]*val26[0])+(val9[1]*val26[1])+(val9[2]*val26[2])+(val9[3]*val26[3])+(val10[0]*val27[0])+(val10[1]*val27[1])+(val10[2]*val27[2])+(val10[3]*val27[3]))*0.25f)+alu4);
      *(data0_2500+(alu2+1875)) = ((((val11[0]*val28[0])+(val11[1]*val28[1])+(val11[2]*val28[2])+(val11[3]*val28[3])+(val12[0]*val29[0])+(val12[1]*val29[1])+(val12[2]*val29[2])+(val12[3]*val29[3])+(val13[0]*val30[0])+(val13[1]*val30[1])+(val13[2]*val30[2])+(val13[3]*val30[3])+(val14[0]*val31[0])+(val14[1]*val31[1])+(val14[2]*val31[2])+(val14[3]*val31[3]))*0.25f)+alu4);
      *(data0_2500+alu2) = ((((val15[0]*val32[0])+(val15[1]*val32[1])+(val15[2]*val32[2])+(val15[3]*val32[3])+(val0[0]*val17[0])+(val0[1]*val17[1])+(val0[2]*val17[2])+(val0[3]*val17[3])+(val1[0]*val18[0])+(val1[1]*val18[1])+(val1[2]*val18[2])+(val1[3]*val18[3])+(val2[0]*val19[0])+(val2[1]*val19[1])+(val2[2]*val19[2])+(val2[3]*val19[3]))*0.25f)+alu4);
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_E_4_25_4_4n1(float* restrict data0_1600, float* restrict data1_1600) {
  for (int Lidx0 = 0; Lidx0 < 4; Lidx0++) {
    for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
      for (int Lidx2 = 0; Lidx2 < 4; Lidx2++) {
        int alu0 = (Lidx2<<2);
        float4 val0 = (*((float4*)((data1_1600+((Lidx0<<4)+alu0+(Lidx1<<6))))));
        *((float4*)((data0_1600+((Lidx1<<4)+alu0+(Lidx0*400))))) = val0;
      }
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_E_4_25_4_4n2(float* restrict data0_1600, float* restrict data1_1600) {
  for (int Lidx0 = 0; Lidx0 < 4; Lidx0++) {
    for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
      for (int Lidx2 = 0; Lidx2 < 4; Lidx2++) {
        int alu0 = (Lidx2<<2);
        float4 val0 = (*((float4*)((data1_1600+((Lidx0<<4)+alu0+(Lidx1<<6))))));
        *((float4*)((data0_1600+((Lidx1<<4)+alu0+(Lidx0*400))))) = val0;
      }
    }
  }
}


void jepa_context_r_100_25n2(float* restrict data0_100, float* restrict data1_2500) {
  for (int Lidx1 = 0; Lidx1 < 100; Lidx1++) {
    int alu0 = (Lidx1*25);
    float val0 = (*(data1_2500+(alu0+1)));
    float val1 = (*(data1_2500+(alu0+2)));
    float val2 = (*(data1_2500+(alu0+3)));
    float val3 = (*(data1_2500+(alu0+4)));
    float val4 = (*(data1_2500+(alu0+5)));
    float val5 = (*(data1_2500+(alu0+6)));
    float val6 = (*(data1_2500+(alu0+7)));
    float val7 = (*(data1_2500+(alu0+8)));
    float val8 = (*(data1_2500+(alu0+9)));
    float val9 = (*(data1_2500+(alu0+10)));
    float val10 = (*(data1_2500+(alu0+11)));
    float val11 = (*(data1_2500+(alu0+12)));
    float val12 = (*(data1_2500+(alu0+13)));
    float val13 = (*(data1_2500+(alu0+14)));
    float val14 = (*(data1_2500+(alu0+15)));
    float val15 = (*(data1_2500+(alu0+16)));
    float val16 = (*(data1_2500+(alu0+17)));
    float val17 = (*(data1_2500+(alu0+18)));
    float val18 = (*(data1_2500+(alu0+19)));
    float val19 = (*(data1_2500+(alu0+20)));
    float val20 = (*(data1_2500+(alu0+21)));
    float val21 = (*(data1_2500+(alu0+22)));
    float val22 = (*(data1_2500+(alu0+23)));
    float val23 = (*(data1_2500+(alu0+24)));
    float val24 = (*(data1_2500+alu0));
    float alu1 = ((val24<val0)?val0:val24);
    float alu2 = ((alu1<val1)?val1:alu1);
    float alu3 = ((alu2<val2)?val2:alu2);
    float alu4 = ((alu3<val3)?val3:alu3);
    float alu5 = ((alu4<val4)?val4:alu4);
    float alu6 = ((alu5<val5)?val5:alu5);
    float alu7 = ((alu6<val6)?val6:alu6);
    float alu8 = ((alu7<val7)?val7:alu7);
    float alu9 = ((alu8<val8)?val8:alu8);
    float alu10 = ((alu9<val9)?val9:alu9);
    float alu11 = ((alu10<val10)?val10:alu10);
    float alu12 = ((alu11<val11)?val11:alu11);
    float alu13 = ((alu12<val12)?val12:alu12);
    float alu14 = ((alu13<val13)?val13:alu13);
    float alu15 = ((alu14<val14)?val14:alu14);
    float alu16 = ((alu15<val15)?val15:alu15);
    float alu17 = ((alu16<val16)?val16:alu16);
    float alu18 = ((alu17<val17)?val17:alu17);
    float alu19 = ((alu18<val18)?val18:alu18);
    float alu20 = ((alu19<val19)?val19:alu19);
    float alu21 = ((alu20<val20)?val20:alu20);
    float alu22 = ((alu21<val21)?val21:alu21);
    float alu23 = ((alu22<val22)?val22:alu22);
    float alu24 = ((alu23<val23)?val23:alu23);
    *(data0_100+Lidx1) = alu24;
  }
}


void jepa_context_r_100_25n3(float* restrict data0_100, float* restrict data1_2500, float* restrict data2_100) {
  for (int Lidx1 = 0; Lidx1 < 100; Lidx1++) {
    int alu0 = (Lidx1*25);
    float val0 = (*(data1_2500+(alu0+1)));
    float val1 = (*(data1_2500+(alu0+2)));
    float val2 = (*(data1_2500+(alu0+3)));
    float val3 = (*(data1_2500+(alu0+4)));
    float val4 = (*(data1_2500+(alu0+5)));
    float val5 = (*(data1_2500+(alu0+6)));
    float val6 = (*(data1_2500+(alu0+7)));
    float val7 = (*(data1_2500+(alu0+8)));
    float val8 = (*(data1_2500+(alu0+9)));
    float val9 = (*(data1_2500+(alu0+10)));
    float val10 = (*(data1_2500+(alu0+11)));
    float val11 = (*(data1_2500+(alu0+12)));
    float val12 = (*(data1_2500+alu0));
    float val13 = (*(data2_100+Lidx1));
    float val14 = (*(data1_2500+(alu0+13)));
    float val15 = (*(data1_2500+(alu0+14)));
    float val16 = (*(data1_2500+(alu0+15)));
    float val17 = (*(data1_2500+(alu0+16)));
    float val18 = (*(data1_2500+(alu0+17)));
    float val19 = (*(data1_2500+(alu0+18)));
    float val20 = (*(data1_2500+(alu0+19)));
    float val21 = (*(data1_2500+(alu0+20)));
    float val22 = (*(data1_2500+(alu0+21)));
    float val23 = (*(data1_2500+(alu0+22)));
    float val24 = (*(data1_2500+(alu0+23)));
    float val25 = (*(data1_2500+(alu0+24)));
    float alu1 = ((val0-val13)*1.4426950408889634f);
    _Bool alu2 = (alu1!=alu1);
    float alu3 = ((alu1!=((float)(-__builtin_inff())))?alu1:0.0f);
    float alu4 = (alu2?0.0f:alu3);
    float alu5 = ((alu1!=((float)(__builtin_inff())))?alu4:0.0f);
    float alu6 = ((alu5<0.0f)?-0.5f:0.5f);
    int cast0 = ((int)((alu5+alu6)));
    float alu7 = ((val1-val13)*1.4426950408889634f);
    _Bool alu8 = (alu7!=alu7);
    float alu9 = ((alu7!=((float)(-__builtin_inff())))?alu7:0.0f);
    float alu10 = (alu8?0.0f:alu9);
    float alu11 = ((alu7!=((float)(__builtin_inff())))?alu10:0.0f);
    float alu12 = ((alu11<0.0f)?-0.5f:0.5f);
    int cast1 = ((int)((alu11+alu12)));
    float alu13 = ((val2-val13)*1.4426950408889634f);
    _Bool alu14 = (alu13!=alu13);
    float alu15 = ((alu13!=((float)(-__builtin_inff())))?alu13:0.0f);
    float alu16 = (alu14?0.0f:alu15);
    float alu17 = ((alu13!=((float)(__builtin_inff())))?alu16:0.0f);
    float alu18 = ((alu17<0.0f)?-0.5f:0.5f);
    int cast2 = ((int)((alu17+alu18)));
    float alu19 = ((val3-val13)*1.4426950408889634f);
    _Bool alu20 = (alu19!=alu19);
    float alu21 = ((alu19!=((float)(-__builtin_inff())))?alu19:0.0f);
    float alu22 = (alu20?0.0f:alu21);
    float alu23 = ((alu19!=((float)(__builtin_inff())))?alu22:0.0f);
    float alu24 = ((alu23<0.0f)?-0.5f:0.5f);
    int cast3 = ((int)((alu23+alu24)));
    float alu25 = ((val4-val13)*1.4426950408889634f);
    _Bool alu26 = (alu25!=alu25);
    float alu27 = ((alu25!=((float)(-__builtin_inff())))?alu25:0.0f);
    float alu28 = (alu26?0.0f:alu27);
    float alu29 = ((alu25!=((float)(__builtin_inff())))?alu28:0.0f);
    float alu30 = ((alu29<0.0f)?-0.5f:0.5f);
    int cast4 = ((int)((alu29+alu30)));
    float alu31 = ((val5-val13)*1.4426950408889634f);
    _Bool alu32 = (alu31!=alu31);
    float alu33 = ((alu31!=((float)(-__builtin_inff())))?alu31:0.0f);
    float alu34 = (alu32?0.0f:alu33);
    float alu35 = ((alu31!=((float)(__builtin_inff())))?alu34:0.0f);
    float alu36 = ((alu35<0.0f)?-0.5f:0.5f);
    int cast5 = ((int)((alu35+alu36)));
    float alu37 = ((val6-val13)*1.4426950408889634f);
    _Bool alu38 = (alu37!=alu37);
    float alu39 = ((alu37!=((float)(-__builtin_inff())))?alu37:0.0f);
    float alu40 = (alu38?0.0f:alu39);
    float alu41 = ((alu37!=((float)(__builtin_inff())))?alu40:0.0f);
    float alu42 = ((alu41<0.0f)?-0.5f:0.5f);
    int cast6 = ((int)((alu41+alu42)));
    float alu43 = ((val7-val13)*1.4426950408889634f);
    _Bool alu44 = (alu43!=alu43);
    float alu45 = ((alu43!=((float)(-__builtin_inff())))?alu43:0.0f);
    float alu46 = (alu44?0.0f:alu45);
    float alu47 = ((alu43!=((float)(__builtin_inff())))?alu46:0.0f);
    float alu48 = ((alu47<0.0f)?-0.5f:0.5f);
    int cast7 = ((int)((alu47+alu48)));
    float alu49 = ((val8-val13)*1.4426950408889634f);
    _Bool alu50 = (alu49!=alu49);
    float alu51 = ((alu49!=((float)(-__builtin_inff())))?alu49:0.0f);
    float alu52 = (alu50?0.0f:alu51);
    float alu53 = ((alu49!=((float)(__builtin_inff())))?alu52:0.0f);
    float alu54 = ((alu53<0.0f)?-0.5f:0.5f);
    int cast8 = ((int)((alu53+alu54)));
    float alu55 = ((val9-val13)*1.4426950408889634f);
    _Bool alu56 = (alu55!=alu55);
    float alu57 = ((alu55!=((float)(-__builtin_inff())))?alu55:0.0f);
    float alu58 = (alu56?0.0f:alu57);
    float alu59 = ((alu55!=((float)(__builtin_inff())))?alu58:0.0f);
    float alu60 = ((alu59<0.0f)?-0.5f:0.5f);
    int cast9 = ((int)((alu59+alu60)));
    float alu61 = ((val10-val13)*1.4426950408889634f);
    _Bool alu62 = (alu61!=alu61);
    float alu63 = ((alu61!=((float)(-__builtin_inff())))?alu61:0.0f);
    float alu64 = (alu62?0.0f:alu63);
    float alu65 = ((alu61!=((float)(__builtin_inff())))?alu64:0.0f);
    float alu66 = ((alu65<0.0f)?-0.5f:0.5f);
    int cast10 = ((int)((alu65+alu66)));
    float alu67 = ((val11-val13)*1.4426950408889634f);
    _Bool alu68 = (alu67!=alu67);
    float alu69 = ((alu67!=((float)(-__builtin_inff())))?alu67:0.0f);
    float alu70 = (alu68?0.0f:alu69);
    float alu71 = ((alu67!=((float)(__builtin_inff())))?alu70:0.0f);
    float alu72 = ((alu71<0.0f)?-0.5f:0.5f);
    int cast11 = ((int)((alu71+alu72)));
    float alu73 = ((val14-val13)*1.4426950408889634f);
    _Bool alu74 = (alu73!=alu73);
    float alu75 = ((alu73!=((float)(-__builtin_inff())))?alu73:0.0f);
    float alu76 = (alu74?0.0f:alu75);
    float alu77 = ((alu73!=((float)(__builtin_inff())))?alu76:0.0f);
    float alu78 = ((alu77<0.0f)?-0.5f:0.5f);
    int cast12 = ((int)((alu77+alu78)));
    float alu79 = ((val15-val13)*1.4426950408889634f);
    _Bool alu80 = (alu79!=alu79);
    float alu81 = ((alu79!=((float)(-__builtin_inff())))?alu79:0.0f);
    float alu82 = (alu80?0.0f:alu81);
    float alu83 = ((alu79!=((float)(__builtin_inff())))?alu82:0.0f);
    float alu84 = ((alu83<0.0f)?-0.5f:0.5f);
    int cast13 = ((int)((alu83+alu84)));
    float alu85 = ((val16-val13)*1.4426950408889634f);
    _Bool alu86 = (alu85!=alu85);
    float alu87 = ((alu85!=((float)(-__builtin_inff())))?alu85:0.0f);
    float alu88 = (alu86?0.0f:alu87);
    float alu89 = ((alu85!=((float)(__builtin_inff())))?alu88:0.0f);
    float alu90 = ((alu89<0.0f)?-0.5f:0.5f);
    int cast14 = ((int)((alu89+alu90)));
    float alu91 = ((val17-val13)*1.4426950408889634f);
    _Bool alu92 = (alu91!=alu91);
    float alu93 = ((alu91!=((float)(-__builtin_inff())))?alu91:0.0f);
    float alu94 = (alu92?0.0f:alu93);
    float alu95 = ((alu91!=((float)(__builtin_inff())))?alu94:0.0f);
    float alu96 = ((alu95<0.0f)?-0.5f:0.5f);
    int cast15 = ((int)((alu95+alu96)));
    float alu97 = ((val18-val13)*1.4426950408889634f);
    _Bool alu98 = (alu97!=alu97);
    float alu99 = ((alu97!=((float)(-__builtin_inff())))?alu97:0.0f);
    float alu100 = (alu98?0.0f:alu99);
    float alu101 = ((alu97!=((float)(__builtin_inff())))?alu100:0.0f);
    float alu102 = ((alu101<0.0f)?-0.5f:0.5f);
    int cast16 = ((int)((alu101+alu102)));
    float alu103 = ((val19-val13)*1.4426950408889634f);
    _Bool alu104 = (alu103!=alu103);
    float alu105 = ((alu103!=((float)(-__builtin_inff())))?alu103:0.0f);
    float alu106 = (alu104?0.0f:alu105);
    float alu107 = ((alu103!=((float)(__builtin_inff())))?alu106:0.0f);
    float alu108 = ((alu107<0.0f)?-0.5f:0.5f);
    int cast17 = ((int)((alu107+alu108)));
    float alu109 = ((val20-val13)*1.4426950408889634f);
    _Bool alu110 = (alu109!=alu109);
    float alu111 = ((alu109!=((float)(-__builtin_inff())))?alu109:0.0f);
    float alu112 = (alu110?0.0f:alu111);
    float alu113 = ((alu109!=((float)(__builtin_inff())))?alu112:0.0f);
    float alu114 = ((alu113<0.0f)?-0.5f:0.5f);
    int cast18 = ((int)((alu113+alu114)));
    float alu115 = ((val21-val13)*1.4426950408889634f);
    _Bool alu116 = (alu115!=alu115);
    float alu117 = ((alu115!=((float)(-__builtin_inff())))?alu115:0.0f);
    float alu118 = (alu116?0.0f:alu117);
    float alu119 = ((alu115!=((float)(__builtin_inff())))?alu118:0.0f);
    float alu120 = ((alu119<0.0f)?-0.5f:0.5f);
    int cast19 = ((int)((alu119+alu120)));
    float alu121 = ((val22-val13)*1.4426950408889634f);
    _Bool alu122 = (alu121!=alu121);
    float alu123 = ((alu121!=((float)(-__builtin_inff())))?alu121:0.0f);
    float alu124 = (alu122?0.0f:alu123);
    float alu125 = ((alu121!=((float)(__builtin_inff())))?alu124:0.0f);
    float alu126 = ((alu125<0.0f)?-0.5f:0.5f);
    int cast20 = ((int)((alu125+alu126)));
    float alu127 = ((val23-val13)*1.4426950408889634f);
    _Bool alu128 = (alu127!=alu127);
    float alu129 = ((alu127!=((float)(-__builtin_inff())))?alu127:0.0f);
    float alu130 = (alu128?0.0f:alu129);
    float alu131 = ((alu127!=((float)(__builtin_inff())))?alu130:0.0f);
    float alu132 = ((alu131<0.0f)?-0.5f:0.5f);
    int cast21 = ((int)((alu131+alu132)));
    float alu133 = ((val24-val13)*1.4426950408889634f);
    _Bool alu134 = (alu133!=alu133);
    float alu135 = ((alu133!=((float)(-__builtin_inff())))?alu133:0.0f);
    float alu136 = (alu134?0.0f:alu135);
    float alu137 = ((alu133!=((float)(__builtin_inff())))?alu136:0.0f);
    float alu138 = ((alu137<0.0f)?-0.5f:0.5f);
    int cast22 = ((int)((alu137+alu138)));
    float alu139 = ((val25-val13)*1.4426950408889634f);
    _Bool alu140 = (alu139!=alu139);
    float alu141 = ((alu139!=((float)(-__builtin_inff())))?alu139:0.0f);
    float alu142 = (alu140?0.0f:alu141);
    float alu143 = ((alu139!=((float)(__builtin_inff())))?alu142:0.0f);
    float alu144 = ((alu143<0.0f)?-0.5f:0.5f);
    int cast23 = ((int)((alu143+alu144)));
    float alu145 = ((val12-val13)*1.4426950408889634f);
    _Bool alu146 = (alu145!=alu145);
    float alu147 = ((alu145!=((float)(-__builtin_inff())))?alu145:0.0f);
    float alu148 = (alu146?0.0f:alu147);
    float alu149 = ((alu145!=((float)(__builtin_inff())))?alu148:0.0f);
    float alu150 = ((alu149<0.0f)?-0.5f:0.5f);
    int cast24 = ((int)((alu149+alu150)));
    int alu151 = ((cast0<0)?1:0);
    int alu152 = ((cast0+alu151)>>1);
    int alu153 = ((cast1<0)?1:0);
    int alu154 = ((cast1+alu153)>>1);
    int alu155 = ((cast2<0)?1:0);
    int alu156 = ((cast2+alu155)>>1);
    int alu157 = ((cast3<0)?1:0);
    int alu158 = ((cast3+alu157)>>1);
    int alu159 = ((cast4<0)?1:0);
    int alu160 = ((cast4+alu159)>>1);
    int alu161 = ((cast5<0)?1:0);
    int alu162 = ((cast5+alu161)>>1);
    int alu163 = ((cast6<0)?1:0);
    int alu164 = ((cast6+alu163)>>1);
    int alu165 = ((cast7<0)?1:0);
    int alu166 = ((cast7+alu165)>>1);
    int alu167 = ((cast8<0)?1:0);
    int alu168 = ((cast8+alu167)>>1);
    int alu169 = ((cast9<0)?1:0);
    int alu170 = ((cast9+alu169)>>1);
    int alu171 = ((cast10<0)?1:0);
    int alu172 = ((cast10+alu171)>>1);
    int alu173 = ((cast11<0)?1:0);
    int alu174 = ((cast11+alu173)>>1);
    int alu175 = ((cast12<0)?1:0);
    int alu176 = ((cast12+alu175)>>1);
    int alu177 = ((cast13<0)?1:0);
    int alu178 = ((cast13+alu177)>>1);
    int alu179 = ((cast14<0)?1:0);
    int alu180 = ((cast14+alu179)>>1);
    int alu181 = ((cast15<0)?1:0);
    int alu182 = ((cast15+alu181)>>1);
    int alu183 = ((cast16<0)?1:0);
    int alu184 = ((cast16+alu183)>>1);
    int alu185 = ((cast17<0)?1:0);
    int alu186 = ((cast17+alu185)>>1);
    int alu187 = ((cast18<0)?1:0);
    int alu188 = ((cast18+alu187)>>1);
    int alu189 = ((cast19<0)?1:0);
    int alu190 = ((cast19+alu189)>>1);
    int alu191 = ((cast20<0)?1:0);
    int alu192 = ((cast20+alu191)>>1);
    int alu193 = ((cast21<0)?1:0);
    int alu194 = ((cast21+alu193)>>1);
    int alu195 = ((cast22<0)?1:0);
    int alu196 = ((cast22+alu195)>>1);
    int alu197 = ((cast23<0)?1:0);
    int alu198 = ((cast23+alu197)>>1);
    int alu199 = ((cast24<0)?1:0);
    int alu200 = ((cast24+alu199)>>1);
    float alu201 = (alu5-((float)(cast0)));
    float alu202 = (alu11-((float)(cast1)));
    float alu203 = (alu149-((float)(cast24)));
    float alu204 = (((alu1<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu201)+0.001339262701f)*alu201)+0.009618384764f)*alu201)+0.05550347269f)*alu201)+0.2402264476f)*alu201)+0.6931471825f)*alu201)+1.0f)*__builtin_bit_cast(float, (int)(((alu152+127)<<23)))*__builtin_bit_cast(float, (int)((((cast0-alu152)+127)<<23)))));
    float alu205 = ((alu1<-150.0f)?0.0f:alu204);
    float alu206 = (((alu145<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu203)+0.001339262701f)*alu203)+0.009618384764f)*alu203)+0.05550347269f)*alu203)+0.2402264476f)*alu203)+0.6931471825f)*alu203)+1.0f)*__builtin_bit_cast(float, (int)(((alu200+127)<<23)))*__builtin_bit_cast(float, (int)((((cast24-alu200)+127)<<23)))));
    float alu207 = ((alu145<-150.0f)?0.0f:alu206);
    float alu208 = (alu2?((float)(__builtin_nanf(""))):alu205);
    float alu209 = (alu146?((float)(__builtin_nanf(""))):alu207);
    float alu210 = (((alu7<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu202)+0.001339262701f)*alu202)+0.009618384764f)*alu202)+0.05550347269f)*alu202)+0.2402264476f)*alu202)+0.6931471825f)*alu202)+1.0f)*__builtin_bit_cast(float, (int)(((alu154+127)<<23)))*__builtin_bit_cast(float, (int)((((cast1-alu154)+127)<<23)))));
    float alu211 = ((alu7<-150.0f)?0.0f:alu210);
    float alu212 = (alu8?((float)(__builtin_nanf(""))):alu211);
    float alu213 = (alu17-((float)(cast2)));
    float alu214 = (((alu13<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu213)+0.001339262701f)*alu213)+0.009618384764f)*alu213)+0.05550347269f)*alu213)+0.2402264476f)*alu213)+0.6931471825f)*alu213)+1.0f)*__builtin_bit_cast(float, (int)(((alu156+127)<<23)))*__builtin_bit_cast(float, (int)((((cast2-alu156)+127)<<23)))));
    float alu215 = ((alu13<-150.0f)?0.0f:alu214);
    float alu216 = (alu14?((float)(__builtin_nanf(""))):alu215);
    float alu217 = (alu23-((float)(cast3)));
    float alu218 = (((alu19<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu217)+0.001339262701f)*alu217)+0.009618384764f)*alu217)+0.05550347269f)*alu217)+0.2402264476f)*alu217)+0.6931471825f)*alu217)+1.0f)*__builtin_bit_cast(float, (int)(((alu158+127)<<23)))*__builtin_bit_cast(float, (int)((((cast3-alu158)+127)<<23)))));
    float alu219 = ((alu19<-150.0f)?0.0f:alu218);
    float alu220 = (alu20?((float)(__builtin_nanf(""))):alu219);
    float alu221 = (alu29-((float)(cast4)));
    float alu222 = (((alu25<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu221)+0.001339262701f)*alu221)+0.009618384764f)*alu221)+0.05550347269f)*alu221)+0.2402264476f)*alu221)+0.6931471825f)*alu221)+1.0f)*__builtin_bit_cast(float, (int)(((alu160+127)<<23)))*__builtin_bit_cast(float, (int)((((cast4-alu160)+127)<<23)))));
    float alu223 = ((alu25<-150.0f)?0.0f:alu222);
    float alu224 = (alu26?((float)(__builtin_nanf(""))):alu223);
    float alu225 = (alu35-((float)(cast5)));
    float alu226 = (((alu31<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu225)+0.001339262701f)*alu225)+0.009618384764f)*alu225)+0.05550347269f)*alu225)+0.2402264476f)*alu225)+0.6931471825f)*alu225)+1.0f)*__builtin_bit_cast(float, (int)(((alu162+127)<<23)))*__builtin_bit_cast(float, (int)((((cast5-alu162)+127)<<23)))));
    float alu227 = ((alu31<-150.0f)?0.0f:alu226);
    float alu228 = (alu32?((float)(__builtin_nanf(""))):alu227);
    float alu229 = (alu41-((float)(cast6)));
    float alu230 = (((alu37<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu229)+0.001339262701f)*alu229)+0.009618384764f)*alu229)+0.05550347269f)*alu229)+0.2402264476f)*alu229)+0.6931471825f)*alu229)+1.0f)*__builtin_bit_cast(float, (int)(((alu164+127)<<23)))*__builtin_bit_cast(float, (int)((((cast6-alu164)+127)<<23)))));
    float alu231 = ((alu37<-150.0f)?0.0f:alu230);
    float alu232 = (alu38?((float)(__builtin_nanf(""))):alu231);
    float alu233 = (alu47-((float)(cast7)));
    float alu234 = (((alu43<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu233)+0.001339262701f)*alu233)+0.009618384764f)*alu233)+0.05550347269f)*alu233)+0.2402264476f)*alu233)+0.6931471825f)*alu233)+1.0f)*__builtin_bit_cast(float, (int)(((alu166+127)<<23)))*__builtin_bit_cast(float, (int)((((cast7-alu166)+127)<<23)))));
    float alu235 = ((alu43<-150.0f)?0.0f:alu234);
    float alu236 = (alu44?((float)(__builtin_nanf(""))):alu235);
    float alu237 = (alu53-((float)(cast8)));
    float alu238 = (((alu49<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu237)+0.001339262701f)*alu237)+0.009618384764f)*alu237)+0.05550347269f)*alu237)+0.2402264476f)*alu237)+0.6931471825f)*alu237)+1.0f)*__builtin_bit_cast(float, (int)(((alu168+127)<<23)))*__builtin_bit_cast(float, (int)((((cast8-alu168)+127)<<23)))));
    float alu239 = ((alu49<-150.0f)?0.0f:alu238);
    float alu240 = (alu50?((float)(__builtin_nanf(""))):alu239);
    float alu241 = (alu59-((float)(cast9)));
    float alu242 = (((alu55<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu241)+0.001339262701f)*alu241)+0.009618384764f)*alu241)+0.05550347269f)*alu241)+0.2402264476f)*alu241)+0.6931471825f)*alu241)+1.0f)*__builtin_bit_cast(float, (int)(((alu170+127)<<23)))*__builtin_bit_cast(float, (int)((((cast9-alu170)+127)<<23)))));
    float alu243 = ((alu55<-150.0f)?0.0f:alu242);
    float alu244 = (alu56?((float)(__builtin_nanf(""))):alu243);
    float alu245 = (alu65-((float)(cast10)));
    float alu246 = (((alu61<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu245)+0.001339262701f)*alu245)+0.009618384764f)*alu245)+0.05550347269f)*alu245)+0.2402264476f)*alu245)+0.6931471825f)*alu245)+1.0f)*__builtin_bit_cast(float, (int)(((alu172+127)<<23)))*__builtin_bit_cast(float, (int)((((cast10-alu172)+127)<<23)))));
    float alu247 = ((alu61<-150.0f)?0.0f:alu246);
    float alu248 = (alu62?((float)(__builtin_nanf(""))):alu247);
    float alu249 = (alu71-((float)(cast11)));
    float alu250 = (((alu67<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu249)+0.001339262701f)*alu249)+0.009618384764f)*alu249)+0.05550347269f)*alu249)+0.2402264476f)*alu249)+0.6931471825f)*alu249)+1.0f)*__builtin_bit_cast(float, (int)(((alu174+127)<<23)))*__builtin_bit_cast(float, (int)((((cast11-alu174)+127)<<23)))));
    float alu251 = ((alu67<-150.0f)?0.0f:alu250);
    float alu252 = (alu68?((float)(__builtin_nanf(""))):alu251);
    float alu253 = (alu77-((float)(cast12)));
    float alu254 = (((alu73<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu253)+0.001339262701f)*alu253)+0.009618384764f)*alu253)+0.05550347269f)*alu253)+0.2402264476f)*alu253)+0.6931471825f)*alu253)+1.0f)*__builtin_bit_cast(float, (int)(((alu176+127)<<23)))*__builtin_bit_cast(float, (int)((((cast12-alu176)+127)<<23)))));
    float alu255 = ((alu73<-150.0f)?0.0f:alu254);
    float alu256 = (alu74?((float)(__builtin_nanf(""))):alu255);
    float alu257 = (alu83-((float)(cast13)));
    float alu258 = (((alu79<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu257)+0.001339262701f)*alu257)+0.009618384764f)*alu257)+0.05550347269f)*alu257)+0.2402264476f)*alu257)+0.6931471825f)*alu257)+1.0f)*__builtin_bit_cast(float, (int)(((alu178+127)<<23)))*__builtin_bit_cast(float, (int)((((cast13-alu178)+127)<<23)))));
    float alu259 = ((alu79<-150.0f)?0.0f:alu258);
    float alu260 = (alu80?((float)(__builtin_nanf(""))):alu259);
    float alu261 = (alu89-((float)(cast14)));
    float alu262 = (((alu85<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu261)+0.001339262701f)*alu261)+0.009618384764f)*alu261)+0.05550347269f)*alu261)+0.2402264476f)*alu261)+0.6931471825f)*alu261)+1.0f)*__builtin_bit_cast(float, (int)(((alu180+127)<<23)))*__builtin_bit_cast(float, (int)((((cast14-alu180)+127)<<23)))));
    float alu263 = ((alu85<-150.0f)?0.0f:alu262);
    float alu264 = (alu86?((float)(__builtin_nanf(""))):alu263);
    float alu265 = (alu95-((float)(cast15)));
    float alu266 = (((alu91<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu265)+0.001339262701f)*alu265)+0.009618384764f)*alu265)+0.05550347269f)*alu265)+0.2402264476f)*alu265)+0.6931471825f)*alu265)+1.0f)*__builtin_bit_cast(float, (int)(((alu182+127)<<23)))*__builtin_bit_cast(float, (int)((((cast15-alu182)+127)<<23)))));
    float alu267 = ((alu91<-150.0f)?0.0f:alu266);
    float alu268 = (alu92?((float)(__builtin_nanf(""))):alu267);
    float alu269 = (alu101-((float)(cast16)));
    float alu270 = (((alu97<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu269)+0.001339262701f)*alu269)+0.009618384764f)*alu269)+0.05550347269f)*alu269)+0.2402264476f)*alu269)+0.6931471825f)*alu269)+1.0f)*__builtin_bit_cast(float, (int)(((alu184+127)<<23)))*__builtin_bit_cast(float, (int)((((cast16-alu184)+127)<<23)))));
    float alu271 = ((alu97<-150.0f)?0.0f:alu270);
    float alu272 = (alu98?((float)(__builtin_nanf(""))):alu271);
    float alu273 = (alu107-((float)(cast17)));
    float alu274 = (((alu103<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu273)+0.001339262701f)*alu273)+0.009618384764f)*alu273)+0.05550347269f)*alu273)+0.2402264476f)*alu273)+0.6931471825f)*alu273)+1.0f)*__builtin_bit_cast(float, (int)(((alu186+127)<<23)))*__builtin_bit_cast(float, (int)((((cast17-alu186)+127)<<23)))));
    float alu275 = ((alu103<-150.0f)?0.0f:alu274);
    float alu276 = (alu104?((float)(__builtin_nanf(""))):alu275);
    float alu277 = (alu113-((float)(cast18)));
    float alu278 = (((alu109<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu277)+0.001339262701f)*alu277)+0.009618384764f)*alu277)+0.05550347269f)*alu277)+0.2402264476f)*alu277)+0.6931471825f)*alu277)+1.0f)*__builtin_bit_cast(float, (int)(((alu188+127)<<23)))*__builtin_bit_cast(float, (int)((((cast18-alu188)+127)<<23)))));
    float alu279 = ((alu109<-150.0f)?0.0f:alu278);
    float alu280 = (alu110?((float)(__builtin_nanf(""))):alu279);
    float alu281 = (alu119-((float)(cast19)));
    float alu282 = (((alu115<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu281)+0.001339262701f)*alu281)+0.009618384764f)*alu281)+0.05550347269f)*alu281)+0.2402264476f)*alu281)+0.6931471825f)*alu281)+1.0f)*__builtin_bit_cast(float, (int)(((alu190+127)<<23)))*__builtin_bit_cast(float, (int)((((cast19-alu190)+127)<<23)))));
    float alu283 = ((alu115<-150.0f)?0.0f:alu282);
    float alu284 = (alu116?((float)(__builtin_nanf(""))):alu283);
    float alu285 = (alu125-((float)(cast20)));
    float alu286 = (((alu121<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu285)+0.001339262701f)*alu285)+0.009618384764f)*alu285)+0.05550347269f)*alu285)+0.2402264476f)*alu285)+0.6931471825f)*alu285)+1.0f)*__builtin_bit_cast(float, (int)(((alu192+127)<<23)))*__builtin_bit_cast(float, (int)((((cast20-alu192)+127)<<23)))));
    float alu287 = ((alu121<-150.0f)?0.0f:alu286);
    float alu288 = (alu122?((float)(__builtin_nanf(""))):alu287);
    float alu289 = (alu131-((float)(cast21)));
    float alu290 = (((alu127<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu289)+0.001339262701f)*alu289)+0.009618384764f)*alu289)+0.05550347269f)*alu289)+0.2402264476f)*alu289)+0.6931471825f)*alu289)+1.0f)*__builtin_bit_cast(float, (int)(((alu194+127)<<23)))*__builtin_bit_cast(float, (int)((((cast21-alu194)+127)<<23)))));
    float alu291 = ((alu127<-150.0f)?0.0f:alu290);
    float alu292 = (alu128?((float)(__builtin_nanf(""))):alu291);
    float alu293 = (alu137-((float)(cast22)));
    float alu294 = (((alu133<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu293)+0.001339262701f)*alu293)+0.009618384764f)*alu293)+0.05550347269f)*alu293)+0.2402264476f)*alu293)+0.6931471825f)*alu293)+1.0f)*__builtin_bit_cast(float, (int)(((alu196+127)<<23)))*__builtin_bit_cast(float, (int)((((cast22-alu196)+127)<<23)))));
    float alu295 = ((alu133<-150.0f)?0.0f:alu294);
    float alu296 = (alu134?((float)(__builtin_nanf(""))):alu295);
    float alu297 = (alu143-((float)(cast23)));
    float alu298 = (((alu139<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu297)+0.001339262701f)*alu297)+0.009618384764f)*alu297)+0.05550347269f)*alu297)+0.2402264476f)*alu297)+0.6931471825f)*alu297)+1.0f)*__builtin_bit_cast(float, (int)(((alu198+127)<<23)))*__builtin_bit_cast(float, (int)((((cast23-alu198)+127)<<23)))));
    float alu299 = ((alu139<-150.0f)?0.0f:alu298);
    float alu300 = (alu140?((float)(__builtin_nanf(""))):alu299);
    *(data0_100+Lidx1) = (1.0f/(alu209+alu208+alu212+alu216+alu220+alu224+alu228+alu232+alu236+alu240+alu244+alu248+alu252+alu256+alu260+alu264+alu268+alu272+alu276+alu280+alu284+alu288+alu292+alu296+alu300));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_4_25_4_4_25n1(float* restrict data0_1600, float* restrict data1_2500, float* restrict data2_100, float* restrict data3_100, float* restrict data4_1600) {
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 25; Lidx2++) {
      int alu0 = ((Lidx1*625)+(Lidx2*25));
      float val0 = (*(data1_2500+(alu0+1)));
      float val1 = (*(data1_2500+(alu0+2)));
      float val2 = (*(data1_2500+(alu0+3)));
      float val3 = (*(data1_2500+(alu0+4)));
      float val4 = (*(data1_2500+(alu0+5)));
      float val5 = (*(data1_2500+(alu0+6)));
      float val6 = (*(data1_2500+(alu0+7)));
      float val7 = (*(data1_2500+(alu0+8)));
      float val8 = (*(data1_2500+(alu0+9)));
      float val9 = (*(data1_2500+(alu0+10)));
      float val10 = (*(data1_2500+(alu0+11)));
      float val11 = (*(data1_2500+(alu0+12)));
      float val12 = (*(data1_2500+(alu0+13)));
      float val13 = (*(data1_2500+(alu0+14)));
      float val14 = (*(data1_2500+alu0));
      int alu1 = ((Lidx1*25)+Lidx2);
      float val15 = (*(data2_100+alu1));
      float val16 = (*(data1_2500+(alu0+15)));
      float val17 = (*(data1_2500+(alu0+16)));
      float val18 = (*(data1_2500+(alu0+17)));
      float val19 = (*(data1_2500+(alu0+18)));
      float val20 = (*(data1_2500+(alu0+19)));
      float val21 = (*(data1_2500+(alu0+20)));
      float val22 = (*(data1_2500+(alu0+21)));
      float val23 = (*(data1_2500+(alu0+22)));
      float val24 = (*(data1_2500+(alu0+23)));
      float val25 = (*(data1_2500+(alu0+24)));
      float val26 = (*(data3_100+alu1));
      float alu2 = ((val0-val15)*1.4426950408889634f);
      _Bool alu3 = (alu2!=alu2);
      float alu4 = ((alu2!=((float)(-__builtin_inff())))?alu2:0.0f);
      float alu5 = (alu3?0.0f:alu4);
      float alu6 = ((alu2!=((float)(__builtin_inff())))?alu5:0.0f);
      float alu7 = ((alu6<0.0f)?-0.5f:0.5f);
      int cast0 = ((int)((alu6+alu7)));
      float alu8 = ((val1-val15)*1.4426950408889634f);
      _Bool alu9 = (alu8!=alu8);
      float alu10 = ((alu8!=((float)(-__builtin_inff())))?alu8:0.0f);
      float alu11 = (alu9?0.0f:alu10);
      float alu12 = ((alu8!=((float)(__builtin_inff())))?alu11:0.0f);
      float alu13 = ((alu12<0.0f)?-0.5f:0.5f);
      int cast1 = ((int)((alu12+alu13)));
      float alu14 = ((val2-val15)*1.4426950408889634f);
      _Bool alu15 = (alu14!=alu14);
      float alu16 = ((alu14!=((float)(-__builtin_inff())))?alu14:0.0f);
      float alu17 = (alu15?0.0f:alu16);
      float alu18 = ((alu14!=((float)(__builtin_inff())))?alu17:0.0f);
      float alu19 = ((alu18<0.0f)?-0.5f:0.5f);
      int cast2 = ((int)((alu18+alu19)));
      float alu20 = ((val3-val15)*1.4426950408889634f);
      _Bool alu21 = (alu20!=alu20);
      float alu22 = ((alu20!=((float)(-__builtin_inff())))?alu20:0.0f);
      float alu23 = (alu21?0.0f:alu22);
      float alu24 = ((alu20!=((float)(__builtin_inff())))?alu23:0.0f);
      float alu25 = ((alu24<0.0f)?-0.5f:0.5f);
      int cast3 = ((int)((alu24+alu25)));
      float alu26 = ((val4-val15)*1.4426950408889634f);
      _Bool alu27 = (alu26!=alu26);
      float alu28 = ((alu26!=((float)(-__builtin_inff())))?alu26:0.0f);
      float alu29 = (alu27?0.0f:alu28);
      float alu30 = ((alu26!=((float)(__builtin_inff())))?alu29:0.0f);
      float alu31 = ((alu30<0.0f)?-0.5f:0.5f);
      int cast4 = ((int)((alu30+alu31)));
      float alu32 = ((val5-val15)*1.4426950408889634f);
      _Bool alu33 = (alu32!=alu32);
      float alu34 = ((alu32!=((float)(-__builtin_inff())))?alu32:0.0f);
      float alu35 = (alu33?0.0f:alu34);
      float alu36 = ((alu32!=((float)(__builtin_inff())))?alu35:0.0f);
      float alu37 = ((alu36<0.0f)?-0.5f:0.5f);
      int cast5 = ((int)((alu36+alu37)));
      float alu38 = ((val6-val15)*1.4426950408889634f);
      _Bool alu39 = (alu38!=alu38);
      float alu40 = ((alu38!=((float)(-__builtin_inff())))?alu38:0.0f);
      float alu41 = (alu39?0.0f:alu40);
      float alu42 = ((alu38!=((float)(__builtin_inff())))?alu41:0.0f);
      float alu43 = ((alu42<0.0f)?-0.5f:0.5f);
      int cast6 = ((int)((alu42+alu43)));
      float alu44 = ((val7-val15)*1.4426950408889634f);
      _Bool alu45 = (alu44!=alu44);
      float alu46 = ((alu44!=((float)(-__builtin_inff())))?alu44:0.0f);
      float alu47 = (alu45?0.0f:alu46);
      float alu48 = ((alu44!=((float)(__builtin_inff())))?alu47:0.0f);
      float alu49 = ((alu48<0.0f)?-0.5f:0.5f);
      int cast7 = ((int)((alu48+alu49)));
      float alu50 = ((val8-val15)*1.4426950408889634f);
      _Bool alu51 = (alu50!=alu50);
      float alu52 = ((alu50!=((float)(-__builtin_inff())))?alu50:0.0f);
      float alu53 = (alu51?0.0f:alu52);
      float alu54 = ((alu50!=((float)(__builtin_inff())))?alu53:0.0f);
      float alu55 = ((alu54<0.0f)?-0.5f:0.5f);
      int cast8 = ((int)((alu54+alu55)));
      float alu56 = ((val9-val15)*1.4426950408889634f);
      _Bool alu57 = (alu56!=alu56);
      float alu58 = ((alu56!=((float)(-__builtin_inff())))?alu56:0.0f);
      float alu59 = (alu57?0.0f:alu58);
      float alu60 = ((alu56!=((float)(__builtin_inff())))?alu59:0.0f);
      float alu61 = ((alu60<0.0f)?-0.5f:0.5f);
      int cast9 = ((int)((alu60+alu61)));
      float alu62 = ((val10-val15)*1.4426950408889634f);
      _Bool alu63 = (alu62!=alu62);
      float alu64 = ((alu62!=((float)(-__builtin_inff())))?alu62:0.0f);
      float alu65 = (alu63?0.0f:alu64);
      float alu66 = ((alu62!=((float)(__builtin_inff())))?alu65:0.0f);
      float alu67 = ((alu66<0.0f)?-0.5f:0.5f);
      int cast10 = ((int)((alu66+alu67)));
      float alu68 = ((val11-val15)*1.4426950408889634f);
      _Bool alu69 = (alu68!=alu68);
      float alu70 = ((alu68!=((float)(-__builtin_inff())))?alu68:0.0f);
      float alu71 = (alu69?0.0f:alu70);
      float alu72 = ((alu68!=((float)(__builtin_inff())))?alu71:0.0f);
      float alu73 = ((alu72<0.0f)?-0.5f:0.5f);
      int cast11 = ((int)((alu72+alu73)));
      float alu74 = ((val12-val15)*1.4426950408889634f);
      _Bool alu75 = (alu74!=alu74);
      float alu76 = ((alu74!=((float)(-__builtin_inff())))?alu74:0.0f);
      float alu77 = (alu75?0.0f:alu76);
      float alu78 = ((alu74!=((float)(__builtin_inff())))?alu77:0.0f);
      float alu79 = ((alu78<0.0f)?-0.5f:0.5f);
      int cast12 = ((int)((alu78+alu79)));
      float alu80 = ((val13-val15)*1.4426950408889634f);
      _Bool alu81 = (alu80!=alu80);
      float alu82 = ((alu80!=((float)(-__builtin_inff())))?alu80:0.0f);
      float alu83 = (alu81?0.0f:alu82);
      float alu84 = ((alu80!=((float)(__builtin_inff())))?alu83:0.0f);
      float alu85 = ((alu84<0.0f)?-0.5f:0.5f);
      int cast13 = ((int)((alu84+alu85)));
      float alu86 = ((val16-val15)*1.4426950408889634f);
      _Bool alu87 = (alu86!=alu86);
      float alu88 = ((alu86!=((float)(-__builtin_inff())))?alu86:0.0f);
      float alu89 = (alu87?0.0f:alu88);
      float alu90 = ((alu86!=((float)(__builtin_inff())))?alu89:0.0f);
      float alu91 = ((alu90<0.0f)?-0.5f:0.5f);
      int cast14 = ((int)((alu90+alu91)));
      float alu92 = ((val17-val15)*1.4426950408889634f);
      _Bool alu93 = (alu92!=alu92);
      float alu94 = ((alu92!=((float)(-__builtin_inff())))?alu92:0.0f);
      float alu95 = (alu93?0.0f:alu94);
      float alu96 = ((alu92!=((float)(__builtin_inff())))?alu95:0.0f);
      float alu97 = ((alu96<0.0f)?-0.5f:0.5f);
      int cast15 = ((int)((alu96+alu97)));
      float alu98 = ((val18-val15)*1.4426950408889634f);
      _Bool alu99 = (alu98!=alu98);
      float alu100 = ((alu98!=((float)(-__builtin_inff())))?alu98:0.0f);
      float alu101 = (alu99?0.0f:alu100);
      float alu102 = ((alu98!=((float)(__builtin_inff())))?alu101:0.0f);
      float alu103 = ((alu102<0.0f)?-0.5f:0.5f);
      int cast16 = ((int)((alu102+alu103)));
      float alu104 = ((val19-val15)*1.4426950408889634f);
      _Bool alu105 = (alu104!=alu104);
      float alu106 = ((alu104!=((float)(-__builtin_inff())))?alu104:0.0f);
      float alu107 = (alu105?0.0f:alu106);
      float alu108 = ((alu104!=((float)(__builtin_inff())))?alu107:0.0f);
      float alu109 = ((alu108<0.0f)?-0.5f:0.5f);
      int cast17 = ((int)((alu108+alu109)));
      float alu110 = ((val20-val15)*1.4426950408889634f);
      _Bool alu111 = (alu110!=alu110);
      float alu112 = ((alu110!=((float)(-__builtin_inff())))?alu110:0.0f);
      float alu113 = (alu111?0.0f:alu112);
      float alu114 = ((alu110!=((float)(__builtin_inff())))?alu113:0.0f);
      float alu115 = ((alu114<0.0f)?-0.5f:0.5f);
      int cast18 = ((int)((alu114+alu115)));
      float alu116 = ((val21-val15)*1.4426950408889634f);
      _Bool alu117 = (alu116!=alu116);
      float alu118 = ((alu116!=((float)(-__builtin_inff())))?alu116:0.0f);
      float alu119 = (alu117?0.0f:alu118);
      float alu120 = ((alu116!=((float)(__builtin_inff())))?alu119:0.0f);
      float alu121 = ((alu120<0.0f)?-0.5f:0.5f);
      int cast19 = ((int)((alu120+alu121)));
      float alu122 = ((val22-val15)*1.4426950408889634f);
      _Bool alu123 = (alu122!=alu122);
      float alu124 = ((alu122!=((float)(-__builtin_inff())))?alu122:0.0f);
      float alu125 = (alu123?0.0f:alu124);
      float alu126 = ((alu122!=((float)(__builtin_inff())))?alu125:0.0f);
      float alu127 = ((alu126<0.0f)?-0.5f:0.5f);
      int cast20 = ((int)((alu126+alu127)));
      float alu128 = ((val23-val15)*1.4426950408889634f);
      _Bool alu129 = (alu128!=alu128);
      float alu130 = ((alu128!=((float)(-__builtin_inff())))?alu128:0.0f);
      float alu131 = (alu129?0.0f:alu130);
      float alu132 = ((alu128!=((float)(__builtin_inff())))?alu131:0.0f);
      float alu133 = ((alu132<0.0f)?-0.5f:0.5f);
      int cast21 = ((int)((alu132+alu133)));
      float alu134 = ((val24-val15)*1.4426950408889634f);
      _Bool alu135 = (alu134!=alu134);
      float alu136 = ((alu134!=((float)(-__builtin_inff())))?alu134:0.0f);
      float alu137 = (alu135?0.0f:alu136);
      float alu138 = ((alu134!=((float)(__builtin_inff())))?alu137:0.0f);
      float alu139 = ((alu138<0.0f)?-0.5f:0.5f);
      int cast22 = ((int)((alu138+alu139)));
      float alu140 = ((val25-val15)*1.4426950408889634f);
      _Bool alu141 = (alu140!=alu140);
      float alu142 = ((alu140!=((float)(-__builtin_inff())))?alu140:0.0f);
      float alu143 = (alu141?0.0f:alu142);
      float alu144 = ((alu140!=((float)(__builtin_inff())))?alu143:0.0f);
      float alu145 = ((alu144<0.0f)?-0.5f:0.5f);
      int cast23 = ((int)((alu144+alu145)));
      float alu146 = ((val14-val15)*1.4426950408889634f);
      _Bool alu147 = (alu146!=alu146);
      float alu148 = ((alu146!=((float)(-__builtin_inff())))?alu146:0.0f);
      float alu149 = (alu147?0.0f:alu148);
      float alu150 = ((alu146!=((float)(__builtin_inff())))?alu149:0.0f);
      float alu151 = ((alu150<0.0f)?-0.5f:0.5f);
      int cast24 = ((int)((alu150+alu151)));
      int alu152 = ((cast0<0)?1:0);
      int alu153 = ((cast0+alu152)>>1);
      int alu154 = ((cast1<0)?1:0);
      int alu155 = ((cast1+alu154)>>1);
      int alu156 = ((cast2<0)?1:0);
      int alu157 = ((cast2+alu156)>>1);
      int alu158 = ((cast3<0)?1:0);
      int alu159 = ((cast3+alu158)>>1);
      int alu160 = ((cast4<0)?1:0);
      int alu161 = ((cast4+alu160)>>1);
      int alu162 = ((cast5<0)?1:0);
      int alu163 = ((cast5+alu162)>>1);
      int alu164 = ((cast6<0)?1:0);
      int alu165 = ((cast6+alu164)>>1);
      int alu166 = ((cast7<0)?1:0);
      int alu167 = ((cast7+alu166)>>1);
      int alu168 = ((cast8<0)?1:0);
      int alu169 = ((cast8+alu168)>>1);
      int alu170 = ((cast9<0)?1:0);
      int alu171 = ((cast9+alu170)>>1);
      int alu172 = ((cast10<0)?1:0);
      int alu173 = ((cast10+alu172)>>1);
      int alu174 = ((cast11<0)?1:0);
      int alu175 = ((cast11+alu174)>>1);
      int alu176 = ((cast12<0)?1:0);
      int alu177 = ((cast12+alu176)>>1);
      int alu178 = ((cast13<0)?1:0);
      int alu179 = ((cast13+alu178)>>1);
      int alu180 = ((cast14<0)?1:0);
      int alu181 = ((cast14+alu180)>>1);
      int alu182 = ((cast15<0)?1:0);
      int alu183 = ((cast15+alu182)>>1);
      int alu184 = ((cast16<0)?1:0);
      int alu185 = ((cast16+alu184)>>1);
      int alu186 = ((cast17<0)?1:0);
      int alu187 = ((cast17+alu186)>>1);
      int alu188 = ((cast18<0)?1:0);
      int alu189 = ((cast18+alu188)>>1);
      int alu190 = ((cast19<0)?1:0);
      int alu191 = ((cast19+alu190)>>1);
      int alu192 = ((cast20<0)?1:0);
      int alu193 = ((cast20+alu192)>>1);
      int alu194 = ((cast21<0)?1:0);
      int alu195 = ((cast21+alu194)>>1);
      int alu196 = ((cast22<0)?1:0);
      int alu197 = ((cast22+alu196)>>1);
      int alu198 = ((cast23<0)?1:0);
      int alu199 = ((cast23+alu198)>>1);
      int alu200 = ((cast24<0)?1:0);
      int alu201 = ((cast24+alu200)>>1);
      float alu202 = (alu6-((float)(cast0)));
      float alu203 = (alu12-((float)(cast1)));
      float alu204 = (alu18-((float)(cast2)));
      float alu205 = (alu24-((float)(cast3)));
      float alu206 = (alu30-((float)(cast4)));
      float alu207 = (alu36-((float)(cast5)));
      float alu208 = (alu42-((float)(cast6)));
      float alu209 = (alu48-((float)(cast7)));
      float alu210 = (alu54-((float)(cast8)));
      float alu211 = (alu60-((float)(cast9)));
      float alu212 = (alu66-((float)(cast10)));
      float alu213 = (alu72-((float)(cast11)));
      float alu214 = (alu78-((float)(cast12)));
      float alu215 = (alu84-((float)(cast13)));
      float alu216 = (alu90-((float)(cast14)));
      float alu217 = (alu96-((float)(cast15)));
      float alu218 = (alu102-((float)(cast16)));
      float alu219 = (alu108-((float)(cast17)));
      float alu220 = (alu114-((float)(cast18)));
      float alu221 = (alu120-((float)(cast19)));
      float alu222 = (alu126-((float)(cast20)));
      float alu223 = (alu132-((float)(cast21)));
      float alu224 = (alu138-((float)(cast22)));
      float alu225 = (alu144-((float)(cast23)));
      float alu226 = (alu150-((float)(cast24)));
      float alu227 = (((alu2<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu202)+0.001339262701f)*alu202)+0.009618384764f)*alu202)+0.05550347269f)*alu202)+0.2402264476f)*alu202)+0.6931471825f)*alu202)+1.0f)*__builtin_bit_cast(float, (int)(((alu153+127)<<23)))*__builtin_bit_cast(float, (int)((((cast0-alu153)+127)<<23)))));
      float alu228 = ((alu2<-150.0f)?0.0f:alu227);
      float alu229 = (((alu8<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu203)+0.001339262701f)*alu203)+0.009618384764f)*alu203)+0.05550347269f)*alu203)+0.2402264476f)*alu203)+0.6931471825f)*alu203)+1.0f)*__builtin_bit_cast(float, (int)(((alu155+127)<<23)))*__builtin_bit_cast(float, (int)((((cast1-alu155)+127)<<23)))));
      float alu230 = ((alu8<-150.0f)?0.0f:alu229);
      float alu231 = (((alu14<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu204)+0.001339262701f)*alu204)+0.009618384764f)*alu204)+0.05550347269f)*alu204)+0.2402264476f)*alu204)+0.6931471825f)*alu204)+1.0f)*__builtin_bit_cast(float, (int)(((alu157+127)<<23)))*__builtin_bit_cast(float, (int)((((cast2-alu157)+127)<<23)))));
      float alu232 = ((alu14<-150.0f)?0.0f:alu231);
      float alu233 = (((alu20<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu205)+0.001339262701f)*alu205)+0.009618384764f)*alu205)+0.05550347269f)*alu205)+0.2402264476f)*alu205)+0.6931471825f)*alu205)+1.0f)*__builtin_bit_cast(float, (int)(((alu159+127)<<23)))*__builtin_bit_cast(float, (int)((((cast3-alu159)+127)<<23)))));
      float alu234 = ((alu20<-150.0f)?0.0f:alu233);
      float alu235 = (((alu26<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu206)+0.001339262701f)*alu206)+0.009618384764f)*alu206)+0.05550347269f)*alu206)+0.2402264476f)*alu206)+0.6931471825f)*alu206)+1.0f)*__builtin_bit_cast(float, (int)(((alu161+127)<<23)))*__builtin_bit_cast(float, (int)((((cast4-alu161)+127)<<23)))));
      float alu236 = ((alu26<-150.0f)?0.0f:alu235);
      float alu237 = (((alu32<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu207)+0.001339262701f)*alu207)+0.009618384764f)*alu207)+0.05550347269f)*alu207)+0.2402264476f)*alu207)+0.6931471825f)*alu207)+1.0f)*__builtin_bit_cast(float, (int)(((alu163+127)<<23)))*__builtin_bit_cast(float, (int)((((cast5-alu163)+127)<<23)))));
      float alu238 = ((alu32<-150.0f)?0.0f:alu237);
      float alu239 = (((alu38<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu208)+0.001339262701f)*alu208)+0.009618384764f)*alu208)+0.05550347269f)*alu208)+0.2402264476f)*alu208)+0.6931471825f)*alu208)+1.0f)*__builtin_bit_cast(float, (int)(((alu165+127)<<23)))*__builtin_bit_cast(float, (int)((((cast6-alu165)+127)<<23)))));
      float alu240 = ((alu38<-150.0f)?0.0f:alu239);
      float alu241 = (((alu44<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu209)+0.001339262701f)*alu209)+0.009618384764f)*alu209)+0.05550347269f)*alu209)+0.2402264476f)*alu209)+0.6931471825f)*alu209)+1.0f)*__builtin_bit_cast(float, (int)(((alu167+127)<<23)))*__builtin_bit_cast(float, (int)((((cast7-alu167)+127)<<23)))));
      float alu242 = ((alu44<-150.0f)?0.0f:alu241);
      float alu243 = (((alu50<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu210)+0.001339262701f)*alu210)+0.009618384764f)*alu210)+0.05550347269f)*alu210)+0.2402264476f)*alu210)+0.6931471825f)*alu210)+1.0f)*__builtin_bit_cast(float, (int)(((alu169+127)<<23)))*__builtin_bit_cast(float, (int)((((cast8-alu169)+127)<<23)))));
      float alu244 = ((alu50<-150.0f)?0.0f:alu243);
      float alu245 = (((alu56<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu211)+0.001339262701f)*alu211)+0.009618384764f)*alu211)+0.05550347269f)*alu211)+0.2402264476f)*alu211)+0.6931471825f)*alu211)+1.0f)*__builtin_bit_cast(float, (int)(((alu171+127)<<23)))*__builtin_bit_cast(float, (int)((((cast9-alu171)+127)<<23)))));
      float alu246 = ((alu56<-150.0f)?0.0f:alu245);
      float alu247 = (((alu62<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu212)+0.001339262701f)*alu212)+0.009618384764f)*alu212)+0.05550347269f)*alu212)+0.2402264476f)*alu212)+0.6931471825f)*alu212)+1.0f)*__builtin_bit_cast(float, (int)(((alu173+127)<<23)))*__builtin_bit_cast(float, (int)((((cast10-alu173)+127)<<23)))));
      float alu248 = ((alu62<-150.0f)?0.0f:alu247);
      float alu249 = (((alu68<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu213)+0.001339262701f)*alu213)+0.009618384764f)*alu213)+0.05550347269f)*alu213)+0.2402264476f)*alu213)+0.6931471825f)*alu213)+1.0f)*__builtin_bit_cast(float, (int)(((alu175+127)<<23)))*__builtin_bit_cast(float, (int)((((cast11-alu175)+127)<<23)))));
      float alu250 = ((alu68<-150.0f)?0.0f:alu249);
      float alu251 = (((alu74<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu214)+0.001339262701f)*alu214)+0.009618384764f)*alu214)+0.05550347269f)*alu214)+0.2402264476f)*alu214)+0.6931471825f)*alu214)+1.0f)*__builtin_bit_cast(float, (int)(((alu177+127)<<23)))*__builtin_bit_cast(float, (int)((((cast12-alu177)+127)<<23)))));
      float alu252 = ((alu74<-150.0f)?0.0f:alu251);
      float alu253 = (((alu80<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu215)+0.001339262701f)*alu215)+0.009618384764f)*alu215)+0.05550347269f)*alu215)+0.2402264476f)*alu215)+0.6931471825f)*alu215)+1.0f)*__builtin_bit_cast(float, (int)(((alu179+127)<<23)))*__builtin_bit_cast(float, (int)((((cast13-alu179)+127)<<23)))));
      float alu254 = ((alu80<-150.0f)?0.0f:alu253);
      float alu255 = (((alu86<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu216)+0.001339262701f)*alu216)+0.009618384764f)*alu216)+0.05550347269f)*alu216)+0.2402264476f)*alu216)+0.6931471825f)*alu216)+1.0f)*__builtin_bit_cast(float, (int)(((alu181+127)<<23)))*__builtin_bit_cast(float, (int)((((cast14-alu181)+127)<<23)))));
      float alu256 = ((alu86<-150.0f)?0.0f:alu255);
      float alu257 = (((alu92<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu217)+0.001339262701f)*alu217)+0.009618384764f)*alu217)+0.05550347269f)*alu217)+0.2402264476f)*alu217)+0.6931471825f)*alu217)+1.0f)*__builtin_bit_cast(float, (int)(((alu183+127)<<23)))*__builtin_bit_cast(float, (int)((((cast15-alu183)+127)<<23)))));
      float alu258 = ((alu92<-150.0f)?0.0f:alu257);
      float alu259 = (((alu98<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu218)+0.001339262701f)*alu218)+0.009618384764f)*alu218)+0.05550347269f)*alu218)+0.2402264476f)*alu218)+0.6931471825f)*alu218)+1.0f)*__builtin_bit_cast(float, (int)(((alu185+127)<<23)))*__builtin_bit_cast(float, (int)((((cast16-alu185)+127)<<23)))));
      float alu260 = ((alu98<-150.0f)?0.0f:alu259);
      float alu261 = (((alu104<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu219)+0.001339262701f)*alu219)+0.009618384764f)*alu219)+0.05550347269f)*alu219)+0.2402264476f)*alu219)+0.6931471825f)*alu219)+1.0f)*__builtin_bit_cast(float, (int)(((alu187+127)<<23)))*__builtin_bit_cast(float, (int)((((cast17-alu187)+127)<<23)))));
      float alu262 = ((alu104<-150.0f)?0.0f:alu261);
      float alu263 = (((alu110<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu220)+0.001339262701f)*alu220)+0.009618384764f)*alu220)+0.05550347269f)*alu220)+0.2402264476f)*alu220)+0.6931471825f)*alu220)+1.0f)*__builtin_bit_cast(float, (int)(((alu189+127)<<23)))*__builtin_bit_cast(float, (int)((((cast18-alu189)+127)<<23)))));
      float alu264 = ((alu110<-150.0f)?0.0f:alu263);
      float alu265 = (((alu116<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu221)+0.001339262701f)*alu221)+0.009618384764f)*alu221)+0.05550347269f)*alu221)+0.2402264476f)*alu221)+0.6931471825f)*alu221)+1.0f)*__builtin_bit_cast(float, (int)(((alu191+127)<<23)))*__builtin_bit_cast(float, (int)((((cast19-alu191)+127)<<23)))));
      float alu266 = ((alu116<-150.0f)?0.0f:alu265);
      float alu267 = (((alu122<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu222)+0.001339262701f)*alu222)+0.009618384764f)*alu222)+0.05550347269f)*alu222)+0.2402264476f)*alu222)+0.6931471825f)*alu222)+1.0f)*__builtin_bit_cast(float, (int)(((alu193+127)<<23)))*__builtin_bit_cast(float, (int)((((cast20-alu193)+127)<<23)))));
      float alu268 = ((alu122<-150.0f)?0.0f:alu267);
      float alu269 = (((alu128<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu223)+0.001339262701f)*alu223)+0.009618384764f)*alu223)+0.05550347269f)*alu223)+0.2402264476f)*alu223)+0.6931471825f)*alu223)+1.0f)*__builtin_bit_cast(float, (int)(((alu195+127)<<23)))*__builtin_bit_cast(float, (int)((((cast21-alu195)+127)<<23)))));
      float alu270 = ((alu128<-150.0f)?0.0f:alu269);
      float alu271 = (((alu134<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu224)+0.001339262701f)*alu224)+0.009618384764f)*alu224)+0.05550347269f)*alu224)+0.2402264476f)*alu224)+0.6931471825f)*alu224)+1.0f)*__builtin_bit_cast(float, (int)(((alu197+127)<<23)))*__builtin_bit_cast(float, (int)((((cast22-alu197)+127)<<23)))));
      float alu272 = ((alu134<-150.0f)?0.0f:alu271);
      float alu273 = (((alu140<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu225)+0.001339262701f)*alu225)+0.009618384764f)*alu225)+0.05550347269f)*alu225)+0.2402264476f)*alu225)+0.6931471825f)*alu225)+1.0f)*__builtin_bit_cast(float, (int)(((alu199+127)<<23)))*__builtin_bit_cast(float, (int)((((cast23-alu199)+127)<<23)))));
      float alu274 = ((alu140<-150.0f)?0.0f:alu273);
      float alu275 = (((alu146<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu226)+0.001339262701f)*alu226)+0.009618384764f)*alu226)+0.05550347269f)*alu226)+0.2402264476f)*alu226)+0.6931471825f)*alu226)+1.0f)*__builtin_bit_cast(float, (int)(((alu201+127)<<23)))*__builtin_bit_cast(float, (int)((((cast24-alu201)+127)<<23)))));
      float alu276 = ((alu146<-150.0f)?0.0f:alu275);
      float alu277 = (alu3?((float)(__builtin_nanf(""))):alu228);
      float alu278 = (alu9?((float)(__builtin_nanf(""))):alu230);
      float alu279 = (alu15?((float)(__builtin_nanf(""))):alu232);
      float alu280 = (alu21?((float)(__builtin_nanf(""))):alu234);
      float alu281 = (alu27?((float)(__builtin_nanf(""))):alu236);
      float alu282 = (alu33?((float)(__builtin_nanf(""))):alu238);
      float alu283 = (alu39?((float)(__builtin_nanf(""))):alu240);
      float alu284 = (alu45?((float)(__builtin_nanf(""))):alu242);
      float alu285 = (alu51?((float)(__builtin_nanf(""))):alu244);
      float alu286 = (alu57?((float)(__builtin_nanf(""))):alu246);
      float alu287 = (alu63?((float)(__builtin_nanf(""))):alu248);
      float alu288 = (alu69?((float)(__builtin_nanf(""))):alu250);
      float alu289 = (alu75?((float)(__builtin_nanf(""))):alu252);
      float alu290 = (alu81?((float)(__builtin_nanf(""))):alu254);
      float alu291 = (alu87?((float)(__builtin_nanf(""))):alu256);
      float alu292 = (alu93?((float)(__builtin_nanf(""))):alu258);
      float alu293 = (alu99?((float)(__builtin_nanf(""))):alu260);
      float alu294 = (alu105?((float)(__builtin_nanf(""))):alu262);
      float alu295 = (alu111?((float)(__builtin_nanf(""))):alu264);
      float alu296 = (alu117?((float)(__builtin_nanf(""))):alu266);
      float alu297 = (alu123?((float)(__builtin_nanf(""))):alu268);
      float alu298 = (alu129?((float)(__builtin_nanf(""))):alu270);
      float alu299 = (alu135?((float)(__builtin_nanf(""))):alu272);
      float alu300 = (alu141?((float)(__builtin_nanf(""))):alu274);
      float alu301 = (alu147?((float)(__builtin_nanf(""))):alu276);
      for (int Lidx3 = 0; Lidx3 < 4; Lidx3++) {
        int alu302 = (Lidx3<<2);
        int alu303 = ((Lidx1<<4)+alu302);
        float4 val27 = (*((float4*)((data4_1600+(alu303+64)))));
        float4 val28 = (*((float4*)((data4_1600+(alu303+128)))));
        float4 val29 = (*((float4*)((data4_1600+(alu303+192)))));
        float4 val30 = (*((float4*)((data4_1600+(alu303+256)))));
        float4 val31 = (*((float4*)((data4_1600+(alu303+320)))));
        float4 val32 = (*((float4*)((data4_1600+(alu303+384)))));
        float4 val33 = (*((float4*)((data4_1600+(alu303+448)))));
        float4 val34 = (*((float4*)((data4_1600+(alu303+512)))));
        float4 val35 = (*((float4*)((data4_1600+(alu303+576)))));
        float4 val36 = (*((float4*)((data4_1600+(alu303+640)))));
        float4 val37 = (*((float4*)((data4_1600+(alu303+704)))));
        float4 val38 = (*((float4*)((data4_1600+(alu303+768)))));
        float4 val39 = (*((float4*)((data4_1600+(alu303+832)))));
        float4 val40 = (*((float4*)((data4_1600+(alu303+896)))));
        float4 val41 = (*((float4*)((data4_1600+(alu303+960)))));
        float4 val42 = (*((float4*)((data4_1600+(alu303+1024)))));
        float4 val43 = (*((float4*)((data4_1600+(alu303+1088)))));
        float4 val44 = (*((float4*)((data4_1600+(alu303+1152)))));
        float4 val45 = (*((float4*)((data4_1600+(alu303+1216)))));
        float4 val46 = (*((float4*)((data4_1600+(alu303+1280)))));
        float4 val47 = (*((float4*)((data4_1600+(alu303+1344)))));
        float4 val48 = (*((float4*)((data4_1600+(alu303+1408)))));
        float4 val49 = (*((float4*)((data4_1600+(alu303+1472)))));
        float4 val50 = (*((float4*)((data4_1600+(alu303+1536)))));
        float4 val51 = (*((float4*)((data4_1600+alu303))));
        *((float4*)((data0_1600+((Lidx2<<4)+alu302+(Lidx1*400))))) = (float4){(((alu301*val51[0])+(alu277*val27[0])+(alu278*val28[0])+(alu279*val29[0])+(alu280*val30[0])+(alu281*val31[0])+(alu282*val32[0])+(alu283*val33[0])+(alu284*val34[0])+(alu285*val35[0])+(alu286*val36[0])+(alu287*val37[0])+(alu288*val38[0])+(alu289*val39[0])+(alu290*val40[0])+(alu291*val41[0])+(alu292*val42[0])+(alu293*val43[0])+(alu294*val44[0])+(alu295*val45[0])+(alu296*val46[0])+(alu297*val47[0])+(alu298*val48[0])+(alu299*val49[0])+(alu300*val50[0]))*val26),(((alu301*val51[1])+(alu277*val27[1])+(alu278*val28[1])+(alu279*val29[1])+(alu280*val30[1])+(alu281*val31[1])+(alu282*val32[1])+(alu283*val33[1])+(alu284*val34[1])+(alu285*val35[1])+(alu286*val36[1])+(alu287*val37[1])+(alu288*val38[1])+(alu289*val39[1])+(alu290*val40[1])+(alu291*val41[1])+(alu292*val42[1])+(alu293*val43[1])+(alu294*val44[1])+(alu295*val45[1])+(alu296*val46[1])+(alu297*val47[1])+(alu298*val48[1])+(alu299*val49[1])+(alu300*val50[1]))*val26),(((alu301*val51[2])+(alu277*val27[2])+(alu278*val28[2])+(alu279*val29[2])+(alu280*val30[2])+(alu281*val31[2])+(alu282*val32[2])+(alu283*val33[2])+(alu284*val34[2])+(alu285*val35[2])+(alu286*val36[2])+(alu287*val37[2])+(alu288*val38[2])+(alu289*val39[2])+(alu290*val40[2])+(alu291*val41[2])+(alu292*val42[2])+(alu293*val43[2])+(alu294*val44[2])+(alu295*val45[2])+(alu296*val46[2])+(alu297*val47[2])+(alu298*val48[2])+(alu299*val49[2])+(alu300*val50[2]))*val26),(((alu301*val51[3])+(alu277*val27[3])+(alu278*val28[3])+(alu279*val29[3])+(alu280*val30[3])+(alu281*val31[3])+(alu282*val32[3])+(alu283*val33[3])+(alu284*val34[3])+(alu285*val35[3])+(alu286*val36[3])+(alu287*val37[3])+(alu288*val38[3])+(alu289*val39[3])+(alu290*val40[3])+(alu291*val41[3])+(alu292*val42[3])+(alu293*val43[3])+(alu294*val44[3])+(alu295*val45[3])+(alu296*val46[3])+(alu297*val47[3])+(alu298*val48[3])+(alu299*val49[3])+(alu300*val50[3]))*val26)};
      }
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4_4_16n1(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_1600, float* restrict data3_4096, float* restrict data4_64) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 16; Lidx2++) {
      int alu0 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0_0 = 0; Ridx0_0 < 4; Ridx0_0++) {
        int alu5 = ((Ridx0_0*400)+(Lidx1<<4));
        float4 val0 = (*((float4*)((data2_1600+alu5))));
        int alu6 = ((Ridx0_0<<10)+alu0);
        float4 val1 = (*((float4*)((data3_4096+(alu6+64)))));
        float4 val2 = (*((float4*)((data3_4096+(alu6+128)))));
        float4 val3 = (*((float4*)((data3_4096+(alu6+192)))));
        float4 val4 = (*((float4*)((data3_4096+(alu6+960)))));
        float4 val5 = (*((float4*)((data3_4096+alu6))));
        float4 val6 = (*((float4*)((data2_1600+(alu5+4)))));
        float4 val7 = (*((float4*)((data3_4096+(alu6+256)))));
        float4 val8 = (*((float4*)((data3_4096+(alu6+320)))));
        float4 val9 = (*((float4*)((data3_4096+(alu6+384)))));
        float4 val10 = (*((float4*)((data3_4096+(alu6+448)))));
        float4 val11 = (*((float4*)((data2_1600+(alu5+8)))));
        float4 val12 = (*((float4*)((data3_4096+(alu6+512)))));
        float4 val13 = (*((float4*)((data3_4096+(alu6+576)))));
        float4 val14 = (*((float4*)((data3_4096+(alu6+640)))));
        float4 val15 = (*((float4*)((data3_4096+(alu6+704)))));
        float4 val16 = (*((float4*)((data2_1600+(alu5+12)))));
        float4 val17 = (*((float4*)((data3_4096+(alu6+768)))));
        float4 val18 = (*((float4*)((data3_4096+(alu6+832)))));
        float4 val19 = (*((float4*)((data3_4096+(alu6+896)))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val5[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0])+(val6[0]*val7[0])+(val6[1]*val8[0])+(val6[2]*val9[0])+(val6[3]*val10[0])+(val11[0]*val12[0])+(val11[1]*val13[0])+(val11[2]*val14[0])+(val11[3]*val15[0])+(val16[0]*val17[0])+(val16[1]*val18[0])+(val16[2]*val19[0])+(val16[3]*val4[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val5[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1])+(val6[0]*val7[1])+(val6[1]*val8[1])+(val6[2]*val9[1])+(val6[3]*val10[1])+(val11[0]*val12[1])+(val11[1]*val13[1])+(val11[2]*val14[1])+(val11[3]*val15[1])+(val16[0]*val17[1])+(val16[1]*val18[1])+(val16[2]*val19[1])+(val16[3]*val4[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val5[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2])+(val6[0]*val7[2])+(val6[1]*val8[2])+(val6[2]*val9[2])+(val6[3]*val10[2])+(val11[0]*val12[2])+(val11[1]*val13[2])+(val11[2]*val14[2])+(val11[3]*val15[2])+(val16[0]*val17[2])+(val16[1]*val18[2])+(val16[2]*val19[2])+(val16[3]*val4[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val5[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3])+(val6[0]*val7[3])+(val6[1]*val8[3])+(val6[2]*val9[3])+(val6[3]*val10[3])+(val11[0]*val12[3])+(val11[1]*val13[3])+(val11[2]*val14[3])+(val11[3]*val15[3])+(val16[0]*val17[3])+(val16[1]*val18[3])+(val16[2]*val19[3])+(val16[3]*val4[3]));
      }
      int alu12 = ((Lidx1<<6)+alu0);
      float4 val20 = (*((float4*)((data1_1600+alu12))));
      float4 val21 = (*((float4*)((data4_64+alu0))));
      *((float4*)((data0_1600+alu12))) = (float4){(val20[0]+(*(acc0+0))+val21[0]),(val20[1]+(*(acc0+1))+val21[1]),(val20[2]+(*(acc0+2))+val21[2]),(val20[3]+(*(acc0+3))+val21[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4n4(float* restrict data0_25, float* restrict data1_1600) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
      *(acc0+0) = ((*(acc0+0))+val0[0]+val0[1]+val0[2]+val0[3]);
    }
    *(data0_25+Lidx1) = ((*(acc0+0))*0.015625f);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4n5(float* restrict data0_25, float* restrict data1_1600, float* restrict data2_25) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    float val0 = (*(data2_25+Lidx1));
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val1 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
      float alu1 = (val1[0]-val0);
      float alu2 = (val1[1]-val0);
      float alu3 = (val1[2]-val0);
      float alu4 = (val1[3]-val0);
      *(acc0+0) = ((*(acc0+0))+(alu1*alu1)+(alu2*alu2)+(alu3*alu3)+(alu4*alu4));
    }
    *(data0_25+Lidx1) = (1.0f/__builtin_sqrtf((((*(acc0+0))*0.015625f)+1e-05f)));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_E_25_16_4n2(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_25, float* restrict data3_25, float* restrict data4_64, float* restrict data5_64) {
  for (int Lidx0 = 0; Lidx0 < 25; Lidx0++) {
    float val0 = (*(data2_25+Lidx0));
    float val1 = (*(data3_25+Lidx0));
    for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
      int alu0 = (Lidx1<<2);
      int alu1 = ((Lidx0<<6)+alu0);
      float4 val2 = (*((float4*)((data1_1600+alu1))));
      float4 val3 = (*((float4*)((data4_64+alu0))));
      float4 val4 = (*((float4*)((data5_64+alu0))));
      *((float4*)((data0_1600+alu1))) = (float4){(((val2[0]-val0)*val1*val3[0])+val4[0]),(((val2[1]-val0)*val1*val3[1])+val4[1]),(((val2[2]-val0)*val1*val3[2])+val4[2]),(((val2[3]-val0)*val1*val3[3])+val4[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_32_4_16_4n1(float* restrict data0_3200, float* restrict data1_1600, float* restrict data2_8192, float* restrict data3_128) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 32; Lidx2++) {
      int alu0 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
        float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
        int alu5 = ((Ridx0<<9)+alu0);
        float4 val1 = (*((float4*)((data2_8192+(alu5+128)))));
        float4 val2 = (*((float4*)((data2_8192+(alu5+256)))));
        float4 val3 = (*((float4*)((data2_8192+(alu5+384)))));
        float4 val4 = (*((float4*)((data2_8192+alu5))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val4[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val4[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val4[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val4[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3]));
      }
      float4 val5 = (*((float4*)((data3_128+alu0))));
      float alu11 = ((*(acc0+0))+val5[0]);
      float alu12 = ((*(acc0+1))+val5[1]);
      float alu13 = ((*(acc0+2))+val5[2]);
      float alu14 = ((*(acc0+3))+val5[3]);
      float alu15 = ((0.0f<alu11)?alu11:0.0f);
      float alu16 = ((0.0f<alu12)?alu12:0.0f);
      float alu17 = ((0.0f<alu13)?alu13:0.0f);
      float alu18 = ((0.0f<alu14)?alu14:0.0f);
      *((float4*)((data0_3200+((Lidx1<<7)+alu0)))) = (float4){alu15,alu16,alu17,alu18};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4_32_4n1(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_3200, float* restrict data3_8192, float* restrict data4_64) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 16; Lidx2++) {
      int alu0 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 32; Ridx0++) {
        float4 val0 = (*((float4*)((data2_3200+((Ridx0<<2)+(Lidx1<<7))))));
        int alu5 = ((Ridx0<<8)+alu0);
        float4 val1 = (*((float4*)((data3_8192+(alu5+64)))));
        float4 val2 = (*((float4*)((data3_8192+(alu5+128)))));
        float4 val3 = (*((float4*)((data3_8192+(alu5+192)))));
        float4 val4 = (*((float4*)((data3_8192+alu5))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val4[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val4[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val4[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val4[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3]));
      }
      int alu11 = ((Lidx1<<6)+alu0);
      float4 val5 = (*((float4*)((data1_1600+alu11))));
      float4 val6 = (*((float4*)((data4_64+alu0))));
      *((float4*)((data0_1600+alu11))) = (float4){(val5[0]+(*(acc0+0))+val6[0]),(val5[1]+(*(acc0+1))+val6[1]),(val5[2]+(*(acc0+2))+val6[2]),(val5[3]+(*(acc0+3))+val6[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4n6(float* restrict data0_25, float* restrict data1_1600) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
      *(acc0+0) = ((*(acc0+0))+val0[0]+val0[1]+val0[2]+val0[3]);
    }
    *(data0_25+Lidx1) = ((*(acc0+0))*0.015625f);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4n7(float* restrict data0_25, float* restrict data1_1600, float* restrict data2_25) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    float val0 = (*(data2_25+Lidx1));
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val1 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
      float alu1 = (val1[0]-val0);
      float alu2 = (val1[1]-val0);
      float alu3 = (val1[2]-val0);
      float alu4 = (val1[3]-val0);
      *(acc0+0) = ((*(acc0+0))+(alu1*alu1)+(alu2*alu2)+(alu3*alu3)+(alu4*alu4));
    }
    *(data0_25+Lidx1) = (1.0f/__builtin_sqrtf((((*(acc0+0))*0.015625f)+1e-05f)));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_E_25_16_4n3(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_25, float* restrict data3_25, float* restrict data4_64, float* restrict data5_64) {
  for (int Lidx0 = 0; Lidx0 < 25; Lidx0++) {
    float val0 = (*(data2_25+Lidx0));
    float val1 = (*(data3_25+Lidx0));
    for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
      int alu0 = (Lidx1<<2);
      int alu1 = ((Lidx0<<6)+alu0);
      float4 val2 = (*((float4*)((data1_1600+alu1))));
      float4 val3 = (*((float4*)((data4_64+alu0))));
      float4 val4 = (*((float4*)((data5_64+alu0))));
      *((float4*)((data0_1600+alu1))) = (float4){(((val2[0]-val0)*val1*val3[0])+val4[0]),(((val2[1]-val0)*val1*val3[1])+val4[1]),(((val2[2]-val0)*val1*val3[2])+val4[2]),(((val2[3]-val0)*val1*val3[3])+val4[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4_16_4n4(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_4096, float* restrict data3_64) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    int alu0 = (Lidx1<<6);
    for (int Lidx2 = 0; Lidx2 < 16; Lidx2++) {
      int alu1 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
        float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+alu0)))));
        int alu6 = ((Ridx0<<8)+alu1);
        float4 val1 = (*((float4*)((data2_4096+(alu6+64)))));
        float4 val2 = (*((float4*)((data2_4096+(alu6+128)))));
        float4 val3 = (*((float4*)((data2_4096+(alu6+192)))));
        float4 val4 = (*((float4*)((data2_4096+alu6))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val4[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val4[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val4[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val4[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3]));
      }
      float4 val5 = (*((float4*)((data3_64+alu1))));
      *((float4*)((data0_1600+(alu0+alu1)))) = (float4){((*(acc0+0))+val5[0]),((*(acc0+1))+val5[1]),((*(acc0+2))+val5[2]),((*(acc0+3))+val5[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4_16_4n5(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_4096, float* restrict data3_64) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    int alu0 = (Lidx1<<6);
    for (int Lidx2 = 0; Lidx2 < 16; Lidx2++) {
      int alu1 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
        float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+alu0)))));
        int alu6 = ((Ridx0<<8)+alu1);
        float4 val1 = (*((float4*)((data2_4096+(alu6+64)))));
        float4 val2 = (*((float4*)((data2_4096+(alu6+128)))));
        float4 val3 = (*((float4*)((data2_4096+(alu6+192)))));
        float4 val4 = (*((float4*)((data2_4096+alu6))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val4[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val4[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val4[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val4[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3]));
      }
      float4 val5 = (*((float4*)((data3_64+alu1))));
      *((float4*)((data0_1600+(alu0+alu1)))) = (float4){((*(acc0+0))+val5[0]),((*(acc0+1))+val5[1]),((*(acc0+2))+val5[2]),((*(acc0+3))+val5[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4_16_4n6(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_4096, float* restrict data3_64) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    int alu0 = (Lidx1<<6);
    for (int Lidx2 = 0; Lidx2 < 16; Lidx2++) {
      int alu1 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
        float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+alu0)))));
        int alu6 = ((Ridx0<<8)+alu1);
        float4 val1 = (*((float4*)((data2_4096+(alu6+64)))));
        float4 val2 = (*((float4*)((data2_4096+(alu6+128)))));
        float4 val3 = (*((float4*)((data2_4096+(alu6+192)))));
        float4 val4 = (*((float4*)((data2_4096+alu6))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val4[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val4[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val4[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val4[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3]));
      }
      float4 val5 = (*((float4*)((data3_64+alu1))));
      *((float4*)((data0_1600+(alu0+alu1)))) = (float4){((*(acc0+0))+val5[0]),((*(acc0+1))+val5[1]),((*(acc0+2))+val5[2]),((*(acc0+3))+val5[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_25_4_16n2(float* restrict data0_2500, float* restrict data1_1600, float* restrict data2_1600, float* restrict data3_24) {
  for (int Lidx2 = 0; Lidx2 < 25; Lidx2++) {
    int alu0 = (Lidx2<<6);
    float4 val0 = (*((float4*)((data1_1600+(alu0+4)))));
    float4 val1 = (*((float4*)((data1_1600+(alu0+8)))));
    float4 val2 = (*((float4*)((data1_1600+(alu0+12)))));
    float4 val3 = (*((float4*)((data1_1600+(alu0+16)))));
    float4 val4 = (*((float4*)((data1_1600+(alu0+20)))));
    float4 val5 = (*((float4*)((data1_1600+(alu0+24)))));
    float4 val6 = (*((float4*)((data1_1600+(alu0+28)))));
    float4 val7 = (*((float4*)((data1_1600+(alu0+32)))));
    float4 val8 = (*((float4*)((data1_1600+(alu0+36)))));
    float4 val9 = (*((float4*)((data1_1600+(alu0+40)))));
    float4 val10 = (*((float4*)((data1_1600+(alu0+44)))));
    float4 val11 = (*((float4*)((data1_1600+(alu0+48)))));
    float4 val12 = (*((float4*)((data1_1600+(alu0+52)))));
    float4 val13 = (*((float4*)((data1_1600+(alu0+56)))));
    float4 val14 = (*((float4*)((data1_1600+(alu0+60)))));
    float4 val15 = (*((float4*)((data1_1600+alu0))));
    for (int Lidx3 = 0; Lidx3 < 25; Lidx3++) {
      float val16 = ((0<Lidx3)?*(data3_24+(Lidx3+-1)):0.0f);
      int alu1 = (Lidx3<<6);
      float4 val17 = (*((float4*)((data2_1600+(alu1+4)))));
      float4 val18 = (*((float4*)((data2_1600+(alu1+8)))));
      float4 val19 = (*((float4*)((data2_1600+(alu1+12)))));
      float4 val20 = (*((float4*)((data2_1600+(alu1+16)))));
      float4 val21 = (*((float4*)((data2_1600+(alu1+20)))));
      float4 val22 = (*((float4*)((data2_1600+(alu1+24)))));
      float4 val23 = (*((float4*)((data2_1600+(alu1+28)))));
      float4 val24 = (*((float4*)((data2_1600+(alu1+32)))));
      float4 val25 = (*((float4*)((data2_1600+(alu1+36)))));
      float4 val26 = (*((float4*)((data2_1600+(alu1+40)))));
      float4 val27 = (*((float4*)((data2_1600+(alu1+44)))));
      float4 val28 = (*((float4*)((data2_1600+(alu1+48)))));
      float4 val29 = (*((float4*)((data2_1600+(alu1+52)))));
      float4 val30 = (*((float4*)((data2_1600+(alu1+56)))));
      float4 val31 = (*((float4*)((data2_1600+(alu1+60)))));
      float4 val32 = (*((float4*)((data2_1600+alu1))));
      int alu2 = ((Lidx2*25)+Lidx3);
      float alu3 = ((Lidx3<1)?1.0f:val16);
      float alu4 = ((alu3+-1.0f)*1000000000.0f);
      *(data0_2500+(alu2+625)) = ((((val3[0]*val20[0])+(val3[1]*val20[1])+(val3[2]*val20[2])+(val3[3]*val20[3])+(val4[0]*val21[0])+(val4[1]*val21[1])+(val4[2]*val21[2])+(val4[3]*val21[3])+(val5[0]*val22[0])+(val5[1]*val22[1])+(val5[2]*val22[2])+(val5[3]*val22[3])+(val6[0]*val23[0])+(val6[1]*val23[1])+(val6[2]*val23[2])+(val6[3]*val23[3]))*0.25f)+alu4);
      *(data0_2500+(alu2+1250)) = ((((val7[0]*val24[0])+(val7[1]*val24[1])+(val7[2]*val24[2])+(val7[3]*val24[3])+(val8[0]*val25[0])+(val8[1]*val25[1])+(val8[2]*val25[2])+(val8[3]*val25[3])+(val9[0]*val26[0])+(val9[1]*val26[1])+(val9[2]*val26[2])+(val9[3]*val26[3])+(val10[0]*val27[0])+(val10[1]*val27[1])+(val10[2]*val27[2])+(val10[3]*val27[3]))*0.25f)+alu4);
      *(data0_2500+(alu2+1875)) = ((((val11[0]*val28[0])+(val11[1]*val28[1])+(val11[2]*val28[2])+(val11[3]*val28[3])+(val12[0]*val29[0])+(val12[1]*val29[1])+(val12[2]*val29[2])+(val12[3]*val29[3])+(val13[0]*val30[0])+(val13[1]*val30[1])+(val13[2]*val30[2])+(val13[3]*val30[3])+(val14[0]*val31[0])+(val14[1]*val31[1])+(val14[2]*val31[2])+(val14[3]*val31[3]))*0.25f)+alu4);
      *(data0_2500+alu2) = ((((val15[0]*val32[0])+(val15[1]*val32[1])+(val15[2]*val32[2])+(val15[3]*val32[3])+(val0[0]*val17[0])+(val0[1]*val17[1])+(val0[2]*val17[2])+(val0[3]*val17[3])+(val1[0]*val18[0])+(val1[1]*val18[1])+(val1[2]*val18[2])+(val1[3]*val18[3])+(val2[0]*val19[0])+(val2[1]*val19[1])+(val2[2]*val19[2])+(val2[3]*val19[3]))*0.25f)+alu4);
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_E_4_25_4_4n3(float* restrict data0_1600, float* restrict data1_1600) {
  for (int Lidx0 = 0; Lidx0 < 4; Lidx0++) {
    for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
      for (int Lidx2 = 0; Lidx2 < 4; Lidx2++) {
        int alu0 = (Lidx2<<2);
        float4 val0 = (*((float4*)((data1_1600+((Lidx0<<4)+alu0+(Lidx1<<6))))));
        *((float4*)((data0_1600+((Lidx1<<4)+alu0+(Lidx0*400))))) = val0;
      }
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_E_4_25_4_4n4(float* restrict data0_1600, float* restrict data1_1600) {
  for (int Lidx0 = 0; Lidx0 < 4; Lidx0++) {
    for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
      for (int Lidx2 = 0; Lidx2 < 4; Lidx2++) {
        int alu0 = (Lidx2<<2);
        float4 val0 = (*((float4*)((data1_1600+((Lidx0<<4)+alu0+(Lidx1<<6))))));
        *((float4*)((data0_1600+((Lidx1<<4)+alu0+(Lidx0*400))))) = val0;
      }
    }
  }
}


void jepa_context_r_100_25n4(float* restrict data0_100, float* restrict data1_2500) {
  for (int Lidx1 = 0; Lidx1 < 100; Lidx1++) {
    int alu0 = (Lidx1*25);
    float val0 = (*(data1_2500+(alu0+1)));
    float val1 = (*(data1_2500+(alu0+2)));
    float val2 = (*(data1_2500+(alu0+3)));
    float val3 = (*(data1_2500+(alu0+4)));
    float val4 = (*(data1_2500+(alu0+5)));
    float val5 = (*(data1_2500+(alu0+6)));
    float val6 = (*(data1_2500+(alu0+7)));
    float val7 = (*(data1_2500+(alu0+8)));
    float val8 = (*(data1_2500+(alu0+9)));
    float val9 = (*(data1_2500+(alu0+10)));
    float val10 = (*(data1_2500+(alu0+11)));
    float val11 = (*(data1_2500+(alu0+12)));
    float val12 = (*(data1_2500+(alu0+13)));
    float val13 = (*(data1_2500+(alu0+14)));
    float val14 = (*(data1_2500+(alu0+15)));
    float val15 = (*(data1_2500+(alu0+16)));
    float val16 = (*(data1_2500+(alu0+17)));
    float val17 = (*(data1_2500+(alu0+18)));
    float val18 = (*(data1_2500+(alu0+19)));
    float val19 = (*(data1_2500+(alu0+20)));
    float val20 = (*(data1_2500+(alu0+21)));
    float val21 = (*(data1_2500+(alu0+22)));
    float val22 = (*(data1_2500+(alu0+23)));
    float val23 = (*(data1_2500+(alu0+24)));
    float val24 = (*(data1_2500+alu0));
    float alu1 = ((val24<val0)?val0:val24);
    float alu2 = ((alu1<val1)?val1:alu1);
    float alu3 = ((alu2<val2)?val2:alu2);
    float alu4 = ((alu3<val3)?val3:alu3);
    float alu5 = ((alu4<val4)?val4:alu4);
    float alu6 = ((alu5<val5)?val5:alu5);
    float alu7 = ((alu6<val6)?val6:alu6);
    float alu8 = ((alu7<val7)?val7:alu7);
    float alu9 = ((alu8<val8)?val8:alu8);
    float alu10 = ((alu9<val9)?val9:alu9);
    float alu11 = ((alu10<val10)?val10:alu10);
    float alu12 = ((alu11<val11)?val11:alu11);
    float alu13 = ((alu12<val12)?val12:alu12);
    float alu14 = ((alu13<val13)?val13:alu13);
    float alu15 = ((alu14<val14)?val14:alu14);
    float alu16 = ((alu15<val15)?val15:alu15);
    float alu17 = ((alu16<val16)?val16:alu16);
    float alu18 = ((alu17<val17)?val17:alu17);
    float alu19 = ((alu18<val18)?val18:alu18);
    float alu20 = ((alu19<val19)?val19:alu19);
    float alu21 = ((alu20<val20)?val20:alu20);
    float alu22 = ((alu21<val21)?val21:alu21);
    float alu23 = ((alu22<val22)?val22:alu22);
    float alu24 = ((alu23<val23)?val23:alu23);
    *(data0_100+Lidx1) = alu24;
  }
}


void jepa_context_r_100_25n5(float* restrict data0_100, float* restrict data1_2500, float* restrict data2_100) {
  for (int Lidx1 = 0; Lidx1 < 100; Lidx1++) {
    int alu0 = (Lidx1*25);
    float val0 = (*(data1_2500+(alu0+1)));
    float val1 = (*(data1_2500+(alu0+2)));
    float val2 = (*(data1_2500+(alu0+3)));
    float val3 = (*(data1_2500+(alu0+4)));
    float val4 = (*(data1_2500+(alu0+5)));
    float val5 = (*(data1_2500+(alu0+6)));
    float val6 = (*(data1_2500+(alu0+7)));
    float val7 = (*(data1_2500+(alu0+8)));
    float val8 = (*(data1_2500+(alu0+9)));
    float val9 = (*(data1_2500+(alu0+10)));
    float val10 = (*(data1_2500+(alu0+11)));
    float val11 = (*(data1_2500+(alu0+12)));
    float val12 = (*(data1_2500+alu0));
    float val13 = (*(data2_100+Lidx1));
    float val14 = (*(data1_2500+(alu0+13)));
    float val15 = (*(data1_2500+(alu0+14)));
    float val16 = (*(data1_2500+(alu0+15)));
    float val17 = (*(data1_2500+(alu0+16)));
    float val18 = (*(data1_2500+(alu0+17)));
    float val19 = (*(data1_2500+(alu0+18)));
    float val20 = (*(data1_2500+(alu0+19)));
    float val21 = (*(data1_2500+(alu0+20)));
    float val22 = (*(data1_2500+(alu0+21)));
    float val23 = (*(data1_2500+(alu0+22)));
    float val24 = (*(data1_2500+(alu0+23)));
    float val25 = (*(data1_2500+(alu0+24)));
    float alu1 = ((val0-val13)*1.4426950408889634f);
    _Bool alu2 = (alu1!=alu1);
    float alu3 = ((alu1!=((float)(-__builtin_inff())))?alu1:0.0f);
    float alu4 = (alu2?0.0f:alu3);
    float alu5 = ((alu1!=((float)(__builtin_inff())))?alu4:0.0f);
    float alu6 = ((alu5<0.0f)?-0.5f:0.5f);
    int cast0 = ((int)((alu5+alu6)));
    float alu7 = ((val1-val13)*1.4426950408889634f);
    _Bool alu8 = (alu7!=alu7);
    float alu9 = ((alu7!=((float)(-__builtin_inff())))?alu7:0.0f);
    float alu10 = (alu8?0.0f:alu9);
    float alu11 = ((alu7!=((float)(__builtin_inff())))?alu10:0.0f);
    float alu12 = ((alu11<0.0f)?-0.5f:0.5f);
    int cast1 = ((int)((alu11+alu12)));
    float alu13 = ((val2-val13)*1.4426950408889634f);
    _Bool alu14 = (alu13!=alu13);
    float alu15 = ((alu13!=((float)(-__builtin_inff())))?alu13:0.0f);
    float alu16 = (alu14?0.0f:alu15);
    float alu17 = ((alu13!=((float)(__builtin_inff())))?alu16:0.0f);
    float alu18 = ((alu17<0.0f)?-0.5f:0.5f);
    int cast2 = ((int)((alu17+alu18)));
    float alu19 = ((val3-val13)*1.4426950408889634f);
    _Bool alu20 = (alu19!=alu19);
    float alu21 = ((alu19!=((float)(-__builtin_inff())))?alu19:0.0f);
    float alu22 = (alu20?0.0f:alu21);
    float alu23 = ((alu19!=((float)(__builtin_inff())))?alu22:0.0f);
    float alu24 = ((alu23<0.0f)?-0.5f:0.5f);
    int cast3 = ((int)((alu23+alu24)));
    float alu25 = ((val4-val13)*1.4426950408889634f);
    _Bool alu26 = (alu25!=alu25);
    float alu27 = ((alu25!=((float)(-__builtin_inff())))?alu25:0.0f);
    float alu28 = (alu26?0.0f:alu27);
    float alu29 = ((alu25!=((float)(__builtin_inff())))?alu28:0.0f);
    float alu30 = ((alu29<0.0f)?-0.5f:0.5f);
    int cast4 = ((int)((alu29+alu30)));
    float alu31 = ((val5-val13)*1.4426950408889634f);
    _Bool alu32 = (alu31!=alu31);
    float alu33 = ((alu31!=((float)(-__builtin_inff())))?alu31:0.0f);
    float alu34 = (alu32?0.0f:alu33);
    float alu35 = ((alu31!=((float)(__builtin_inff())))?alu34:0.0f);
    float alu36 = ((alu35<0.0f)?-0.5f:0.5f);
    int cast5 = ((int)((alu35+alu36)));
    float alu37 = ((val6-val13)*1.4426950408889634f);
    _Bool alu38 = (alu37!=alu37);
    float alu39 = ((alu37!=((float)(-__builtin_inff())))?alu37:0.0f);
    float alu40 = (alu38?0.0f:alu39);
    float alu41 = ((alu37!=((float)(__builtin_inff())))?alu40:0.0f);
    float alu42 = ((alu41<0.0f)?-0.5f:0.5f);
    int cast6 = ((int)((alu41+alu42)));
    float alu43 = ((val7-val13)*1.4426950408889634f);
    _Bool alu44 = (alu43!=alu43);
    float alu45 = ((alu43!=((float)(-__builtin_inff())))?alu43:0.0f);
    float alu46 = (alu44?0.0f:alu45);
    float alu47 = ((alu43!=((float)(__builtin_inff())))?alu46:0.0f);
    float alu48 = ((alu47<0.0f)?-0.5f:0.5f);
    int cast7 = ((int)((alu47+alu48)));
    float alu49 = ((val8-val13)*1.4426950408889634f);
    _Bool alu50 = (alu49!=alu49);
    float alu51 = ((alu49!=((float)(-__builtin_inff())))?alu49:0.0f);
    float alu52 = (alu50?0.0f:alu51);
    float alu53 = ((alu49!=((float)(__builtin_inff())))?alu52:0.0f);
    float alu54 = ((alu53<0.0f)?-0.5f:0.5f);
    int cast8 = ((int)((alu53+alu54)));
    float alu55 = ((val9-val13)*1.4426950408889634f);
    _Bool alu56 = (alu55!=alu55);
    float alu57 = ((alu55!=((float)(-__builtin_inff())))?alu55:0.0f);
    float alu58 = (alu56?0.0f:alu57);
    float alu59 = ((alu55!=((float)(__builtin_inff())))?alu58:0.0f);
    float alu60 = ((alu59<0.0f)?-0.5f:0.5f);
    int cast9 = ((int)((alu59+alu60)));
    float alu61 = ((val10-val13)*1.4426950408889634f);
    _Bool alu62 = (alu61!=alu61);
    float alu63 = ((alu61!=((float)(-__builtin_inff())))?alu61:0.0f);
    float alu64 = (alu62?0.0f:alu63);
    float alu65 = ((alu61!=((float)(__builtin_inff())))?alu64:0.0f);
    float alu66 = ((alu65<0.0f)?-0.5f:0.5f);
    int cast10 = ((int)((alu65+alu66)));
    float alu67 = ((val11-val13)*1.4426950408889634f);
    _Bool alu68 = (alu67!=alu67);
    float alu69 = ((alu67!=((float)(-__builtin_inff())))?alu67:0.0f);
    float alu70 = (alu68?0.0f:alu69);
    float alu71 = ((alu67!=((float)(__builtin_inff())))?alu70:0.0f);
    float alu72 = ((alu71<0.0f)?-0.5f:0.5f);
    int cast11 = ((int)((alu71+alu72)));
    float alu73 = ((val14-val13)*1.4426950408889634f);
    _Bool alu74 = (alu73!=alu73);
    float alu75 = ((alu73!=((float)(-__builtin_inff())))?alu73:0.0f);
    float alu76 = (alu74?0.0f:alu75);
    float alu77 = ((alu73!=((float)(__builtin_inff())))?alu76:0.0f);
    float alu78 = ((alu77<0.0f)?-0.5f:0.5f);
    int cast12 = ((int)((alu77+alu78)));
    float alu79 = ((val15-val13)*1.4426950408889634f);
    _Bool alu80 = (alu79!=alu79);
    float alu81 = ((alu79!=((float)(-__builtin_inff())))?alu79:0.0f);
    float alu82 = (alu80?0.0f:alu81);
    float alu83 = ((alu79!=((float)(__builtin_inff())))?alu82:0.0f);
    float alu84 = ((alu83<0.0f)?-0.5f:0.5f);
    int cast13 = ((int)((alu83+alu84)));
    float alu85 = ((val16-val13)*1.4426950408889634f);
    _Bool alu86 = (alu85!=alu85);
    float alu87 = ((alu85!=((float)(-__builtin_inff())))?alu85:0.0f);
    float alu88 = (alu86?0.0f:alu87);
    float alu89 = ((alu85!=((float)(__builtin_inff())))?alu88:0.0f);
    float alu90 = ((alu89<0.0f)?-0.5f:0.5f);
    int cast14 = ((int)((alu89+alu90)));
    float alu91 = ((val17-val13)*1.4426950408889634f);
    _Bool alu92 = (alu91!=alu91);
    float alu93 = ((alu91!=((float)(-__builtin_inff())))?alu91:0.0f);
    float alu94 = (alu92?0.0f:alu93);
    float alu95 = ((alu91!=((float)(__builtin_inff())))?alu94:0.0f);
    float alu96 = ((alu95<0.0f)?-0.5f:0.5f);
    int cast15 = ((int)((alu95+alu96)));
    float alu97 = ((val18-val13)*1.4426950408889634f);
    _Bool alu98 = (alu97!=alu97);
    float alu99 = ((alu97!=((float)(-__builtin_inff())))?alu97:0.0f);
    float alu100 = (alu98?0.0f:alu99);
    float alu101 = ((alu97!=((float)(__builtin_inff())))?alu100:0.0f);
    float alu102 = ((alu101<0.0f)?-0.5f:0.5f);
    int cast16 = ((int)((alu101+alu102)));
    float alu103 = ((val19-val13)*1.4426950408889634f);
    _Bool alu104 = (alu103!=alu103);
    float alu105 = ((alu103!=((float)(-__builtin_inff())))?alu103:0.0f);
    float alu106 = (alu104?0.0f:alu105);
    float alu107 = ((alu103!=((float)(__builtin_inff())))?alu106:0.0f);
    float alu108 = ((alu107<0.0f)?-0.5f:0.5f);
    int cast17 = ((int)((alu107+alu108)));
    float alu109 = ((val20-val13)*1.4426950408889634f);
    _Bool alu110 = (alu109!=alu109);
    float alu111 = ((alu109!=((float)(-__builtin_inff())))?alu109:0.0f);
    float alu112 = (alu110?0.0f:alu111);
    float alu113 = ((alu109!=((float)(__builtin_inff())))?alu112:0.0f);
    float alu114 = ((alu113<0.0f)?-0.5f:0.5f);
    int cast18 = ((int)((alu113+alu114)));
    float alu115 = ((val21-val13)*1.4426950408889634f);
    _Bool alu116 = (alu115!=alu115);
    float alu117 = ((alu115!=((float)(-__builtin_inff())))?alu115:0.0f);
    float alu118 = (alu116?0.0f:alu117);
    float alu119 = ((alu115!=((float)(__builtin_inff())))?alu118:0.0f);
    float alu120 = ((alu119<0.0f)?-0.5f:0.5f);
    int cast19 = ((int)((alu119+alu120)));
    float alu121 = ((val22-val13)*1.4426950408889634f);
    _Bool alu122 = (alu121!=alu121);
    float alu123 = ((alu121!=((float)(-__builtin_inff())))?alu121:0.0f);
    float alu124 = (alu122?0.0f:alu123);
    float alu125 = ((alu121!=((float)(__builtin_inff())))?alu124:0.0f);
    float alu126 = ((alu125<0.0f)?-0.5f:0.5f);
    int cast20 = ((int)((alu125+alu126)));
    float alu127 = ((val23-val13)*1.4426950408889634f);
    _Bool alu128 = (alu127!=alu127);
    float alu129 = ((alu127!=((float)(-__builtin_inff())))?alu127:0.0f);
    float alu130 = (alu128?0.0f:alu129);
    float alu131 = ((alu127!=((float)(__builtin_inff())))?alu130:0.0f);
    float alu132 = ((alu131<0.0f)?-0.5f:0.5f);
    int cast21 = ((int)((alu131+alu132)));
    float alu133 = ((val24-val13)*1.4426950408889634f);
    _Bool alu134 = (alu133!=alu133);
    float alu135 = ((alu133!=((float)(-__builtin_inff())))?alu133:0.0f);
    float alu136 = (alu134?0.0f:alu135);
    float alu137 = ((alu133!=((float)(__builtin_inff())))?alu136:0.0f);
    float alu138 = ((alu137<0.0f)?-0.5f:0.5f);
    int cast22 = ((int)((alu137+alu138)));
    float alu139 = ((val25-val13)*1.4426950408889634f);
    _Bool alu140 = (alu139!=alu139);
    float alu141 = ((alu139!=((float)(-__builtin_inff())))?alu139:0.0f);
    float alu142 = (alu140?0.0f:alu141);
    float alu143 = ((alu139!=((float)(__builtin_inff())))?alu142:0.0f);
    float alu144 = ((alu143<0.0f)?-0.5f:0.5f);
    int cast23 = ((int)((alu143+alu144)));
    float alu145 = ((val12-val13)*1.4426950408889634f);
    _Bool alu146 = (alu145!=alu145);
    float alu147 = ((alu145!=((float)(-__builtin_inff())))?alu145:0.0f);
    float alu148 = (alu146?0.0f:alu147);
    float alu149 = ((alu145!=((float)(__builtin_inff())))?alu148:0.0f);
    float alu150 = ((alu149<0.0f)?-0.5f:0.5f);
    int cast24 = ((int)((alu149+alu150)));
    int alu151 = ((cast0<0)?1:0);
    int alu152 = ((cast0+alu151)>>1);
    int alu153 = ((cast1<0)?1:0);
    int alu154 = ((cast1+alu153)>>1);
    int alu155 = ((cast2<0)?1:0);
    int alu156 = ((cast2+alu155)>>1);
    int alu157 = ((cast3<0)?1:0);
    int alu158 = ((cast3+alu157)>>1);
    int alu159 = ((cast4<0)?1:0);
    int alu160 = ((cast4+alu159)>>1);
    int alu161 = ((cast5<0)?1:0);
    int alu162 = ((cast5+alu161)>>1);
    int alu163 = ((cast6<0)?1:0);
    int alu164 = ((cast6+alu163)>>1);
    int alu165 = ((cast7<0)?1:0);
    int alu166 = ((cast7+alu165)>>1);
    int alu167 = ((cast8<0)?1:0);
    int alu168 = ((cast8+alu167)>>1);
    int alu169 = ((cast9<0)?1:0);
    int alu170 = ((cast9+alu169)>>1);
    int alu171 = ((cast10<0)?1:0);
    int alu172 = ((cast10+alu171)>>1);
    int alu173 = ((cast11<0)?1:0);
    int alu174 = ((cast11+alu173)>>1);
    int alu175 = ((cast12<0)?1:0);
    int alu176 = ((cast12+alu175)>>1);
    int alu177 = ((cast13<0)?1:0);
    int alu178 = ((cast13+alu177)>>1);
    int alu179 = ((cast14<0)?1:0);
    int alu180 = ((cast14+alu179)>>1);
    int alu181 = ((cast15<0)?1:0);
    int alu182 = ((cast15+alu181)>>1);
    int alu183 = ((cast16<0)?1:0);
    int alu184 = ((cast16+alu183)>>1);
    int alu185 = ((cast17<0)?1:0);
    int alu186 = ((cast17+alu185)>>1);
    int alu187 = ((cast18<0)?1:0);
    int alu188 = ((cast18+alu187)>>1);
    int alu189 = ((cast19<0)?1:0);
    int alu190 = ((cast19+alu189)>>1);
    int alu191 = ((cast20<0)?1:0);
    int alu192 = ((cast20+alu191)>>1);
    int alu193 = ((cast21<0)?1:0);
    int alu194 = ((cast21+alu193)>>1);
    int alu195 = ((cast22<0)?1:0);
    int alu196 = ((cast22+alu195)>>1);
    int alu197 = ((cast23<0)?1:0);
    int alu198 = ((cast23+alu197)>>1);
    int alu199 = ((cast24<0)?1:0);
    int alu200 = ((cast24+alu199)>>1);
    float alu201 = (alu5-((float)(cast0)));
    float alu202 = (alu11-((float)(cast1)));
    float alu203 = (alu149-((float)(cast24)));
    float alu204 = (((alu1<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu201)+0.001339262701f)*alu201)+0.009618384764f)*alu201)+0.05550347269f)*alu201)+0.2402264476f)*alu201)+0.6931471825f)*alu201)+1.0f)*__builtin_bit_cast(float, (int)(((alu152+127)<<23)))*__builtin_bit_cast(float, (int)((((cast0-alu152)+127)<<23)))));
    float alu205 = ((alu1<-150.0f)?0.0f:alu204);
    float alu206 = (((alu145<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu203)+0.001339262701f)*alu203)+0.009618384764f)*alu203)+0.05550347269f)*alu203)+0.2402264476f)*alu203)+0.6931471825f)*alu203)+1.0f)*__builtin_bit_cast(float, (int)(((alu200+127)<<23)))*__builtin_bit_cast(float, (int)((((cast24-alu200)+127)<<23)))));
    float alu207 = ((alu145<-150.0f)?0.0f:alu206);
    float alu208 = (alu2?((float)(__builtin_nanf(""))):alu205);
    float alu209 = (alu146?((float)(__builtin_nanf(""))):alu207);
    float alu210 = (((alu7<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu202)+0.001339262701f)*alu202)+0.009618384764f)*alu202)+0.05550347269f)*alu202)+0.2402264476f)*alu202)+0.6931471825f)*alu202)+1.0f)*__builtin_bit_cast(float, (int)(((alu154+127)<<23)))*__builtin_bit_cast(float, (int)((((cast1-alu154)+127)<<23)))));
    float alu211 = ((alu7<-150.0f)?0.0f:alu210);
    float alu212 = (alu8?((float)(__builtin_nanf(""))):alu211);
    float alu213 = (alu17-((float)(cast2)));
    float alu214 = (((alu13<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu213)+0.001339262701f)*alu213)+0.009618384764f)*alu213)+0.05550347269f)*alu213)+0.2402264476f)*alu213)+0.6931471825f)*alu213)+1.0f)*__builtin_bit_cast(float, (int)(((alu156+127)<<23)))*__builtin_bit_cast(float, (int)((((cast2-alu156)+127)<<23)))));
    float alu215 = ((alu13<-150.0f)?0.0f:alu214);
    float alu216 = (alu14?((float)(__builtin_nanf(""))):alu215);
    float alu217 = (alu23-((float)(cast3)));
    float alu218 = (((alu19<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu217)+0.001339262701f)*alu217)+0.009618384764f)*alu217)+0.05550347269f)*alu217)+0.2402264476f)*alu217)+0.6931471825f)*alu217)+1.0f)*__builtin_bit_cast(float, (int)(((alu158+127)<<23)))*__builtin_bit_cast(float, (int)((((cast3-alu158)+127)<<23)))));
    float alu219 = ((alu19<-150.0f)?0.0f:alu218);
    float alu220 = (alu20?((float)(__builtin_nanf(""))):alu219);
    float alu221 = (alu29-((float)(cast4)));
    float alu222 = (((alu25<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu221)+0.001339262701f)*alu221)+0.009618384764f)*alu221)+0.05550347269f)*alu221)+0.2402264476f)*alu221)+0.6931471825f)*alu221)+1.0f)*__builtin_bit_cast(float, (int)(((alu160+127)<<23)))*__builtin_bit_cast(float, (int)((((cast4-alu160)+127)<<23)))));
    float alu223 = ((alu25<-150.0f)?0.0f:alu222);
    float alu224 = (alu26?((float)(__builtin_nanf(""))):alu223);
    float alu225 = (alu35-((float)(cast5)));
    float alu226 = (((alu31<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu225)+0.001339262701f)*alu225)+0.009618384764f)*alu225)+0.05550347269f)*alu225)+0.2402264476f)*alu225)+0.6931471825f)*alu225)+1.0f)*__builtin_bit_cast(float, (int)(((alu162+127)<<23)))*__builtin_bit_cast(float, (int)((((cast5-alu162)+127)<<23)))));
    float alu227 = ((alu31<-150.0f)?0.0f:alu226);
    float alu228 = (alu32?((float)(__builtin_nanf(""))):alu227);
    float alu229 = (alu41-((float)(cast6)));
    float alu230 = (((alu37<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu229)+0.001339262701f)*alu229)+0.009618384764f)*alu229)+0.05550347269f)*alu229)+0.2402264476f)*alu229)+0.6931471825f)*alu229)+1.0f)*__builtin_bit_cast(float, (int)(((alu164+127)<<23)))*__builtin_bit_cast(float, (int)((((cast6-alu164)+127)<<23)))));
    float alu231 = ((alu37<-150.0f)?0.0f:alu230);
    float alu232 = (alu38?((float)(__builtin_nanf(""))):alu231);
    float alu233 = (alu47-((float)(cast7)));
    float alu234 = (((alu43<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu233)+0.001339262701f)*alu233)+0.009618384764f)*alu233)+0.05550347269f)*alu233)+0.2402264476f)*alu233)+0.6931471825f)*alu233)+1.0f)*__builtin_bit_cast(float, (int)(((alu166+127)<<23)))*__builtin_bit_cast(float, (int)((((cast7-alu166)+127)<<23)))));
    float alu235 = ((alu43<-150.0f)?0.0f:alu234);
    float alu236 = (alu44?((float)(__builtin_nanf(""))):alu235);
    float alu237 = (alu53-((float)(cast8)));
    float alu238 = (((alu49<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu237)+0.001339262701f)*alu237)+0.009618384764f)*alu237)+0.05550347269f)*alu237)+0.2402264476f)*alu237)+0.6931471825f)*alu237)+1.0f)*__builtin_bit_cast(float, (int)(((alu168+127)<<23)))*__builtin_bit_cast(float, (int)((((cast8-alu168)+127)<<23)))));
    float alu239 = ((alu49<-150.0f)?0.0f:alu238);
    float alu240 = (alu50?((float)(__builtin_nanf(""))):alu239);
    float alu241 = (alu59-((float)(cast9)));
    float alu242 = (((alu55<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu241)+0.001339262701f)*alu241)+0.009618384764f)*alu241)+0.05550347269f)*alu241)+0.2402264476f)*alu241)+0.6931471825f)*alu241)+1.0f)*__builtin_bit_cast(float, (int)(((alu170+127)<<23)))*__builtin_bit_cast(float, (int)((((cast9-alu170)+127)<<23)))));
    float alu243 = ((alu55<-150.0f)?0.0f:alu242);
    float alu244 = (alu56?((float)(__builtin_nanf(""))):alu243);
    float alu245 = (alu65-((float)(cast10)));
    float alu246 = (((alu61<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu245)+0.001339262701f)*alu245)+0.009618384764f)*alu245)+0.05550347269f)*alu245)+0.2402264476f)*alu245)+0.6931471825f)*alu245)+1.0f)*__builtin_bit_cast(float, (int)(((alu172+127)<<23)))*__builtin_bit_cast(float, (int)((((cast10-alu172)+127)<<23)))));
    float alu247 = ((alu61<-150.0f)?0.0f:alu246);
    float alu248 = (alu62?((float)(__builtin_nanf(""))):alu247);
    float alu249 = (alu71-((float)(cast11)));
    float alu250 = (((alu67<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu249)+0.001339262701f)*alu249)+0.009618384764f)*alu249)+0.05550347269f)*alu249)+0.2402264476f)*alu249)+0.6931471825f)*alu249)+1.0f)*__builtin_bit_cast(float, (int)(((alu174+127)<<23)))*__builtin_bit_cast(float, (int)((((cast11-alu174)+127)<<23)))));
    float alu251 = ((alu67<-150.0f)?0.0f:alu250);
    float alu252 = (alu68?((float)(__builtin_nanf(""))):alu251);
    float alu253 = (alu77-((float)(cast12)));
    float alu254 = (((alu73<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu253)+0.001339262701f)*alu253)+0.009618384764f)*alu253)+0.05550347269f)*alu253)+0.2402264476f)*alu253)+0.6931471825f)*alu253)+1.0f)*__builtin_bit_cast(float, (int)(((alu176+127)<<23)))*__builtin_bit_cast(float, (int)((((cast12-alu176)+127)<<23)))));
    float alu255 = ((alu73<-150.0f)?0.0f:alu254);
    float alu256 = (alu74?((float)(__builtin_nanf(""))):alu255);
    float alu257 = (alu83-((float)(cast13)));
    float alu258 = (((alu79<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu257)+0.001339262701f)*alu257)+0.009618384764f)*alu257)+0.05550347269f)*alu257)+0.2402264476f)*alu257)+0.6931471825f)*alu257)+1.0f)*__builtin_bit_cast(float, (int)(((alu178+127)<<23)))*__builtin_bit_cast(float, (int)((((cast13-alu178)+127)<<23)))));
    float alu259 = ((alu79<-150.0f)?0.0f:alu258);
    float alu260 = (alu80?((float)(__builtin_nanf(""))):alu259);
    float alu261 = (alu89-((float)(cast14)));
    float alu262 = (((alu85<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu261)+0.001339262701f)*alu261)+0.009618384764f)*alu261)+0.05550347269f)*alu261)+0.2402264476f)*alu261)+0.6931471825f)*alu261)+1.0f)*__builtin_bit_cast(float, (int)(((alu180+127)<<23)))*__builtin_bit_cast(float, (int)((((cast14-alu180)+127)<<23)))));
    float alu263 = ((alu85<-150.0f)?0.0f:alu262);
    float alu264 = (alu86?((float)(__builtin_nanf(""))):alu263);
    float alu265 = (alu95-((float)(cast15)));
    float alu266 = (((alu91<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu265)+0.001339262701f)*alu265)+0.009618384764f)*alu265)+0.05550347269f)*alu265)+0.2402264476f)*alu265)+0.6931471825f)*alu265)+1.0f)*__builtin_bit_cast(float, (int)(((alu182+127)<<23)))*__builtin_bit_cast(float, (int)((((cast15-alu182)+127)<<23)))));
    float alu267 = ((alu91<-150.0f)?0.0f:alu266);
    float alu268 = (alu92?((float)(__builtin_nanf(""))):alu267);
    float alu269 = (alu101-((float)(cast16)));
    float alu270 = (((alu97<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu269)+0.001339262701f)*alu269)+0.009618384764f)*alu269)+0.05550347269f)*alu269)+0.2402264476f)*alu269)+0.6931471825f)*alu269)+1.0f)*__builtin_bit_cast(float, (int)(((alu184+127)<<23)))*__builtin_bit_cast(float, (int)((((cast16-alu184)+127)<<23)))));
    float alu271 = ((alu97<-150.0f)?0.0f:alu270);
    float alu272 = (alu98?((float)(__builtin_nanf(""))):alu271);
    float alu273 = (alu107-((float)(cast17)));
    float alu274 = (((alu103<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu273)+0.001339262701f)*alu273)+0.009618384764f)*alu273)+0.05550347269f)*alu273)+0.2402264476f)*alu273)+0.6931471825f)*alu273)+1.0f)*__builtin_bit_cast(float, (int)(((alu186+127)<<23)))*__builtin_bit_cast(float, (int)((((cast17-alu186)+127)<<23)))));
    float alu275 = ((alu103<-150.0f)?0.0f:alu274);
    float alu276 = (alu104?((float)(__builtin_nanf(""))):alu275);
    float alu277 = (alu113-((float)(cast18)));
    float alu278 = (((alu109<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu277)+0.001339262701f)*alu277)+0.009618384764f)*alu277)+0.05550347269f)*alu277)+0.2402264476f)*alu277)+0.6931471825f)*alu277)+1.0f)*__builtin_bit_cast(float, (int)(((alu188+127)<<23)))*__builtin_bit_cast(float, (int)((((cast18-alu188)+127)<<23)))));
    float alu279 = ((alu109<-150.0f)?0.0f:alu278);
    float alu280 = (alu110?((float)(__builtin_nanf(""))):alu279);
    float alu281 = (alu119-((float)(cast19)));
    float alu282 = (((alu115<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu281)+0.001339262701f)*alu281)+0.009618384764f)*alu281)+0.05550347269f)*alu281)+0.2402264476f)*alu281)+0.6931471825f)*alu281)+1.0f)*__builtin_bit_cast(float, (int)(((alu190+127)<<23)))*__builtin_bit_cast(float, (int)((((cast19-alu190)+127)<<23)))));
    float alu283 = ((alu115<-150.0f)?0.0f:alu282);
    float alu284 = (alu116?((float)(__builtin_nanf(""))):alu283);
    float alu285 = (alu125-((float)(cast20)));
    float alu286 = (((alu121<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu285)+0.001339262701f)*alu285)+0.009618384764f)*alu285)+0.05550347269f)*alu285)+0.2402264476f)*alu285)+0.6931471825f)*alu285)+1.0f)*__builtin_bit_cast(float, (int)(((alu192+127)<<23)))*__builtin_bit_cast(float, (int)((((cast20-alu192)+127)<<23)))));
    float alu287 = ((alu121<-150.0f)?0.0f:alu286);
    float alu288 = (alu122?((float)(__builtin_nanf(""))):alu287);
    float alu289 = (alu131-((float)(cast21)));
    float alu290 = (((alu127<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu289)+0.001339262701f)*alu289)+0.009618384764f)*alu289)+0.05550347269f)*alu289)+0.2402264476f)*alu289)+0.6931471825f)*alu289)+1.0f)*__builtin_bit_cast(float, (int)(((alu194+127)<<23)))*__builtin_bit_cast(float, (int)((((cast21-alu194)+127)<<23)))));
    float alu291 = ((alu127<-150.0f)?0.0f:alu290);
    float alu292 = (alu128?((float)(__builtin_nanf(""))):alu291);
    float alu293 = (alu137-((float)(cast22)));
    float alu294 = (((alu133<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu293)+0.001339262701f)*alu293)+0.009618384764f)*alu293)+0.05550347269f)*alu293)+0.2402264476f)*alu293)+0.6931471825f)*alu293)+1.0f)*__builtin_bit_cast(float, (int)(((alu196+127)<<23)))*__builtin_bit_cast(float, (int)((((cast22-alu196)+127)<<23)))));
    float alu295 = ((alu133<-150.0f)?0.0f:alu294);
    float alu296 = (alu134?((float)(__builtin_nanf(""))):alu295);
    float alu297 = (alu143-((float)(cast23)));
    float alu298 = (((alu139<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu297)+0.001339262701f)*alu297)+0.009618384764f)*alu297)+0.05550347269f)*alu297)+0.2402264476f)*alu297)+0.6931471825f)*alu297)+1.0f)*__builtin_bit_cast(float, (int)(((alu198+127)<<23)))*__builtin_bit_cast(float, (int)((((cast23-alu198)+127)<<23)))));
    float alu299 = ((alu139<-150.0f)?0.0f:alu298);
    float alu300 = (alu140?((float)(__builtin_nanf(""))):alu299);
    *(data0_100+Lidx1) = (1.0f/(alu209+alu208+alu212+alu216+alu220+alu224+alu228+alu232+alu236+alu240+alu244+alu248+alu252+alu256+alu260+alu264+alu268+alu272+alu276+alu280+alu284+alu288+alu292+alu296+alu300));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_4_25_4_4_25n2(float* restrict data0_1600, float* restrict data1_2500, float* restrict data2_100, float* restrict data3_100, float* restrict data4_1600) {
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 25; Lidx2++) {
      int alu0 = ((Lidx1*625)+(Lidx2*25));
      float val0 = (*(data1_2500+(alu0+1)));
      float val1 = (*(data1_2500+(alu0+2)));
      float val2 = (*(data1_2500+(alu0+3)));
      float val3 = (*(data1_2500+(alu0+4)));
      float val4 = (*(data1_2500+(alu0+5)));
      float val5 = (*(data1_2500+(alu0+6)));
      float val6 = (*(data1_2500+(alu0+7)));
      float val7 = (*(data1_2500+(alu0+8)));
      float val8 = (*(data1_2500+(alu0+9)));
      float val9 = (*(data1_2500+(alu0+10)));
      float val10 = (*(data1_2500+(alu0+11)));
      float val11 = (*(data1_2500+(alu0+12)));
      float val12 = (*(data1_2500+(alu0+13)));
      float val13 = (*(data1_2500+(alu0+14)));
      float val14 = (*(data1_2500+alu0));
      int alu1 = ((Lidx1*25)+Lidx2);
      float val15 = (*(data2_100+alu1));
      float val16 = (*(data1_2500+(alu0+15)));
      float val17 = (*(data1_2500+(alu0+16)));
      float val18 = (*(data1_2500+(alu0+17)));
      float val19 = (*(data1_2500+(alu0+18)));
      float val20 = (*(data1_2500+(alu0+19)));
      float val21 = (*(data1_2500+(alu0+20)));
      float val22 = (*(data1_2500+(alu0+21)));
      float val23 = (*(data1_2500+(alu0+22)));
      float val24 = (*(data1_2500+(alu0+23)));
      float val25 = (*(data1_2500+(alu0+24)));
      float val26 = (*(data3_100+alu1));
      float alu2 = ((val0-val15)*1.4426950408889634f);
      _Bool alu3 = (alu2!=alu2);
      float alu4 = ((alu2!=((float)(-__builtin_inff())))?alu2:0.0f);
      float alu5 = (alu3?0.0f:alu4);
      float alu6 = ((alu2!=((float)(__builtin_inff())))?alu5:0.0f);
      float alu7 = ((alu6<0.0f)?-0.5f:0.5f);
      int cast0 = ((int)((alu6+alu7)));
      float alu8 = ((val1-val15)*1.4426950408889634f);
      _Bool alu9 = (alu8!=alu8);
      float alu10 = ((alu8!=((float)(-__builtin_inff())))?alu8:0.0f);
      float alu11 = (alu9?0.0f:alu10);
      float alu12 = ((alu8!=((float)(__builtin_inff())))?alu11:0.0f);
      float alu13 = ((alu12<0.0f)?-0.5f:0.5f);
      int cast1 = ((int)((alu12+alu13)));
      float alu14 = ((val2-val15)*1.4426950408889634f);
      _Bool alu15 = (alu14!=alu14);
      float alu16 = ((alu14!=((float)(-__builtin_inff())))?alu14:0.0f);
      float alu17 = (alu15?0.0f:alu16);
      float alu18 = ((alu14!=((float)(__builtin_inff())))?alu17:0.0f);
      float alu19 = ((alu18<0.0f)?-0.5f:0.5f);
      int cast2 = ((int)((alu18+alu19)));
      float alu20 = ((val3-val15)*1.4426950408889634f);
      _Bool alu21 = (alu20!=alu20);
      float alu22 = ((alu20!=((float)(-__builtin_inff())))?alu20:0.0f);
      float alu23 = (alu21?0.0f:alu22);
      float alu24 = ((alu20!=((float)(__builtin_inff())))?alu23:0.0f);
      float alu25 = ((alu24<0.0f)?-0.5f:0.5f);
      int cast3 = ((int)((alu24+alu25)));
      float alu26 = ((val4-val15)*1.4426950408889634f);
      _Bool alu27 = (alu26!=alu26);
      float alu28 = ((alu26!=((float)(-__builtin_inff())))?alu26:0.0f);
      float alu29 = (alu27?0.0f:alu28);
      float alu30 = ((alu26!=((float)(__builtin_inff())))?alu29:0.0f);
      float alu31 = ((alu30<0.0f)?-0.5f:0.5f);
      int cast4 = ((int)((alu30+alu31)));
      float alu32 = ((val5-val15)*1.4426950408889634f);
      _Bool alu33 = (alu32!=alu32);
      float alu34 = ((alu32!=((float)(-__builtin_inff())))?alu32:0.0f);
      float alu35 = (alu33?0.0f:alu34);
      float alu36 = ((alu32!=((float)(__builtin_inff())))?alu35:0.0f);
      float alu37 = ((alu36<0.0f)?-0.5f:0.5f);
      int cast5 = ((int)((alu36+alu37)));
      float alu38 = ((val6-val15)*1.4426950408889634f);
      _Bool alu39 = (alu38!=alu38);
      float alu40 = ((alu38!=((float)(-__builtin_inff())))?alu38:0.0f);
      float alu41 = (alu39?0.0f:alu40);
      float alu42 = ((alu38!=((float)(__builtin_inff())))?alu41:0.0f);
      float alu43 = ((alu42<0.0f)?-0.5f:0.5f);
      int cast6 = ((int)((alu42+alu43)));
      float alu44 = ((val7-val15)*1.4426950408889634f);
      _Bool alu45 = (alu44!=alu44);
      float alu46 = ((alu44!=((float)(-__builtin_inff())))?alu44:0.0f);
      float alu47 = (alu45?0.0f:alu46);
      float alu48 = ((alu44!=((float)(__builtin_inff())))?alu47:0.0f);
      float alu49 = ((alu48<0.0f)?-0.5f:0.5f);
      int cast7 = ((int)((alu48+alu49)));
      float alu50 = ((val8-val15)*1.4426950408889634f);
      _Bool alu51 = (alu50!=alu50);
      float alu52 = ((alu50!=((float)(-__builtin_inff())))?alu50:0.0f);
      float alu53 = (alu51?0.0f:alu52);
      float alu54 = ((alu50!=((float)(__builtin_inff())))?alu53:0.0f);
      float alu55 = ((alu54<0.0f)?-0.5f:0.5f);
      int cast8 = ((int)((alu54+alu55)));
      float alu56 = ((val9-val15)*1.4426950408889634f);
      _Bool alu57 = (alu56!=alu56);
      float alu58 = ((alu56!=((float)(-__builtin_inff())))?alu56:0.0f);
      float alu59 = (alu57?0.0f:alu58);
      float alu60 = ((alu56!=((float)(__builtin_inff())))?alu59:0.0f);
      float alu61 = ((alu60<0.0f)?-0.5f:0.5f);
      int cast9 = ((int)((alu60+alu61)));
      float alu62 = ((val10-val15)*1.4426950408889634f);
      _Bool alu63 = (alu62!=alu62);
      float alu64 = ((alu62!=((float)(-__builtin_inff())))?alu62:0.0f);
      float alu65 = (alu63?0.0f:alu64);
      float alu66 = ((alu62!=((float)(__builtin_inff())))?alu65:0.0f);
      float alu67 = ((alu66<0.0f)?-0.5f:0.5f);
      int cast10 = ((int)((alu66+alu67)));
      float alu68 = ((val11-val15)*1.4426950408889634f);
      _Bool alu69 = (alu68!=alu68);
      float alu70 = ((alu68!=((float)(-__builtin_inff())))?alu68:0.0f);
      float alu71 = (alu69?0.0f:alu70);
      float alu72 = ((alu68!=((float)(__builtin_inff())))?alu71:0.0f);
      float alu73 = ((alu72<0.0f)?-0.5f:0.5f);
      int cast11 = ((int)((alu72+alu73)));
      float alu74 = ((val12-val15)*1.4426950408889634f);
      _Bool alu75 = (alu74!=alu74);
      float alu76 = ((alu74!=((float)(-__builtin_inff())))?alu74:0.0f);
      float alu77 = (alu75?0.0f:alu76);
      float alu78 = ((alu74!=((float)(__builtin_inff())))?alu77:0.0f);
      float alu79 = ((alu78<0.0f)?-0.5f:0.5f);
      int cast12 = ((int)((alu78+alu79)));
      float alu80 = ((val13-val15)*1.4426950408889634f);
      _Bool alu81 = (alu80!=alu80);
      float alu82 = ((alu80!=((float)(-__builtin_inff())))?alu80:0.0f);
      float alu83 = (alu81?0.0f:alu82);
      float alu84 = ((alu80!=((float)(__builtin_inff())))?alu83:0.0f);
      float alu85 = ((alu84<0.0f)?-0.5f:0.5f);
      int cast13 = ((int)((alu84+alu85)));
      float alu86 = ((val16-val15)*1.4426950408889634f);
      _Bool alu87 = (alu86!=alu86);
      float alu88 = ((alu86!=((float)(-__builtin_inff())))?alu86:0.0f);
      float alu89 = (alu87?0.0f:alu88);
      float alu90 = ((alu86!=((float)(__builtin_inff())))?alu89:0.0f);
      float alu91 = ((alu90<0.0f)?-0.5f:0.5f);
      int cast14 = ((int)((alu90+alu91)));
      float alu92 = ((val17-val15)*1.4426950408889634f);
      _Bool alu93 = (alu92!=alu92);
      float alu94 = ((alu92!=((float)(-__builtin_inff())))?alu92:0.0f);
      float alu95 = (alu93?0.0f:alu94);
      float alu96 = ((alu92!=((float)(__builtin_inff())))?alu95:0.0f);
      float alu97 = ((alu96<0.0f)?-0.5f:0.5f);
      int cast15 = ((int)((alu96+alu97)));
      float alu98 = ((val18-val15)*1.4426950408889634f);
      _Bool alu99 = (alu98!=alu98);
      float alu100 = ((alu98!=((float)(-__builtin_inff())))?alu98:0.0f);
      float alu101 = (alu99?0.0f:alu100);
      float alu102 = ((alu98!=((float)(__builtin_inff())))?alu101:0.0f);
      float alu103 = ((alu102<0.0f)?-0.5f:0.5f);
      int cast16 = ((int)((alu102+alu103)));
      float alu104 = ((val19-val15)*1.4426950408889634f);
      _Bool alu105 = (alu104!=alu104);
      float alu106 = ((alu104!=((float)(-__builtin_inff())))?alu104:0.0f);
      float alu107 = (alu105?0.0f:alu106);
      float alu108 = ((alu104!=((float)(__builtin_inff())))?alu107:0.0f);
      float alu109 = ((alu108<0.0f)?-0.5f:0.5f);
      int cast17 = ((int)((alu108+alu109)));
      float alu110 = ((val20-val15)*1.4426950408889634f);
      _Bool alu111 = (alu110!=alu110);
      float alu112 = ((alu110!=((float)(-__builtin_inff())))?alu110:0.0f);
      float alu113 = (alu111?0.0f:alu112);
      float alu114 = ((alu110!=((float)(__builtin_inff())))?alu113:0.0f);
      float alu115 = ((alu114<0.0f)?-0.5f:0.5f);
      int cast18 = ((int)((alu114+alu115)));
      float alu116 = ((val21-val15)*1.4426950408889634f);
      _Bool alu117 = (alu116!=alu116);
      float alu118 = ((alu116!=((float)(-__builtin_inff())))?alu116:0.0f);
      float alu119 = (alu117?0.0f:alu118);
      float alu120 = ((alu116!=((float)(__builtin_inff())))?alu119:0.0f);
      float alu121 = ((alu120<0.0f)?-0.5f:0.5f);
      int cast19 = ((int)((alu120+alu121)));
      float alu122 = ((val22-val15)*1.4426950408889634f);
      _Bool alu123 = (alu122!=alu122);
      float alu124 = ((alu122!=((float)(-__builtin_inff())))?alu122:0.0f);
      float alu125 = (alu123?0.0f:alu124);
      float alu126 = ((alu122!=((float)(__builtin_inff())))?alu125:0.0f);
      float alu127 = ((alu126<0.0f)?-0.5f:0.5f);
      int cast20 = ((int)((alu126+alu127)));
      float alu128 = ((val23-val15)*1.4426950408889634f);
      _Bool alu129 = (alu128!=alu128);
      float alu130 = ((alu128!=((float)(-__builtin_inff())))?alu128:0.0f);
      float alu131 = (alu129?0.0f:alu130);
      float alu132 = ((alu128!=((float)(__builtin_inff())))?alu131:0.0f);
      float alu133 = ((alu132<0.0f)?-0.5f:0.5f);
      int cast21 = ((int)((alu132+alu133)));
      float alu134 = ((val24-val15)*1.4426950408889634f);
      _Bool alu135 = (alu134!=alu134);
      float alu136 = ((alu134!=((float)(-__builtin_inff())))?alu134:0.0f);
      float alu137 = (alu135?0.0f:alu136);
      float alu138 = ((alu134!=((float)(__builtin_inff())))?alu137:0.0f);
      float alu139 = ((alu138<0.0f)?-0.5f:0.5f);
      int cast22 = ((int)((alu138+alu139)));
      float alu140 = ((val25-val15)*1.4426950408889634f);
      _Bool alu141 = (alu140!=alu140);
      float alu142 = ((alu140!=((float)(-__builtin_inff())))?alu140:0.0f);
      float alu143 = (alu141?0.0f:alu142);
      float alu144 = ((alu140!=((float)(__builtin_inff())))?alu143:0.0f);
      float alu145 = ((alu144<0.0f)?-0.5f:0.5f);
      int cast23 = ((int)((alu144+alu145)));
      float alu146 = ((val14-val15)*1.4426950408889634f);
      _Bool alu147 = (alu146!=alu146);
      float alu148 = ((alu146!=((float)(-__builtin_inff())))?alu146:0.0f);
      float alu149 = (alu147?0.0f:alu148);
      float alu150 = ((alu146!=((float)(__builtin_inff())))?alu149:0.0f);
      float alu151 = ((alu150<0.0f)?-0.5f:0.5f);
      int cast24 = ((int)((alu150+alu151)));
      int alu152 = ((cast0<0)?1:0);
      int alu153 = ((cast0+alu152)>>1);
      int alu154 = ((cast1<0)?1:0);
      int alu155 = ((cast1+alu154)>>1);
      int alu156 = ((cast2<0)?1:0);
      int alu157 = ((cast2+alu156)>>1);
      int alu158 = ((cast3<0)?1:0);
      int alu159 = ((cast3+alu158)>>1);
      int alu160 = ((cast4<0)?1:0);
      int alu161 = ((cast4+alu160)>>1);
      int alu162 = ((cast5<0)?1:0);
      int alu163 = ((cast5+alu162)>>1);
      int alu164 = ((cast6<0)?1:0);
      int alu165 = ((cast6+alu164)>>1);
      int alu166 = ((cast7<0)?1:0);
      int alu167 = ((cast7+alu166)>>1);
      int alu168 = ((cast8<0)?1:0);
      int alu169 = ((cast8+alu168)>>1);
      int alu170 = ((cast9<0)?1:0);
      int alu171 = ((cast9+alu170)>>1);
      int alu172 = ((cast10<0)?1:0);
      int alu173 = ((cast10+alu172)>>1);
      int alu174 = ((cast11<0)?1:0);
      int alu175 = ((cast11+alu174)>>1);
      int alu176 = ((cast12<0)?1:0);
      int alu177 = ((cast12+alu176)>>1);
      int alu178 = ((cast13<0)?1:0);
      int alu179 = ((cast13+alu178)>>1);
      int alu180 = ((cast14<0)?1:0);
      int alu181 = ((cast14+alu180)>>1);
      int alu182 = ((cast15<0)?1:0);
      int alu183 = ((cast15+alu182)>>1);
      int alu184 = ((cast16<0)?1:0);
      int alu185 = ((cast16+alu184)>>1);
      int alu186 = ((cast17<0)?1:0);
      int alu187 = ((cast17+alu186)>>1);
      int alu188 = ((cast18<0)?1:0);
      int alu189 = ((cast18+alu188)>>1);
      int alu190 = ((cast19<0)?1:0);
      int alu191 = ((cast19+alu190)>>1);
      int alu192 = ((cast20<0)?1:0);
      int alu193 = ((cast20+alu192)>>1);
      int alu194 = ((cast21<0)?1:0);
      int alu195 = ((cast21+alu194)>>1);
      int alu196 = ((cast22<0)?1:0);
      int alu197 = ((cast22+alu196)>>1);
      int alu198 = ((cast23<0)?1:0);
      int alu199 = ((cast23+alu198)>>1);
      int alu200 = ((cast24<0)?1:0);
      int alu201 = ((cast24+alu200)>>1);
      float alu202 = (alu6-((float)(cast0)));
      float alu203 = (alu12-((float)(cast1)));
      float alu204 = (alu18-((float)(cast2)));
      float alu205 = (alu24-((float)(cast3)));
      float alu206 = (alu30-((float)(cast4)));
      float alu207 = (alu36-((float)(cast5)));
      float alu208 = (alu42-((float)(cast6)));
      float alu209 = (alu48-((float)(cast7)));
      float alu210 = (alu54-((float)(cast8)));
      float alu211 = (alu60-((float)(cast9)));
      float alu212 = (alu66-((float)(cast10)));
      float alu213 = (alu72-((float)(cast11)));
      float alu214 = (alu78-((float)(cast12)));
      float alu215 = (alu84-((float)(cast13)));
      float alu216 = (alu90-((float)(cast14)));
      float alu217 = (alu96-((float)(cast15)));
      float alu218 = (alu102-((float)(cast16)));
      float alu219 = (alu108-((float)(cast17)));
      float alu220 = (alu114-((float)(cast18)));
      float alu221 = (alu120-((float)(cast19)));
      float alu222 = (alu126-((float)(cast20)));
      float alu223 = (alu132-((float)(cast21)));
      float alu224 = (alu138-((float)(cast22)));
      float alu225 = (alu144-((float)(cast23)));
      float alu226 = (alu150-((float)(cast24)));
      float alu227 = (((alu2<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu202)+0.001339262701f)*alu202)+0.009618384764f)*alu202)+0.05550347269f)*alu202)+0.2402264476f)*alu202)+0.6931471825f)*alu202)+1.0f)*__builtin_bit_cast(float, (int)(((alu153+127)<<23)))*__builtin_bit_cast(float, (int)((((cast0-alu153)+127)<<23)))));
      float alu228 = ((alu2<-150.0f)?0.0f:alu227);
      float alu229 = (((alu8<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu203)+0.001339262701f)*alu203)+0.009618384764f)*alu203)+0.05550347269f)*alu203)+0.2402264476f)*alu203)+0.6931471825f)*alu203)+1.0f)*__builtin_bit_cast(float, (int)(((alu155+127)<<23)))*__builtin_bit_cast(float, (int)((((cast1-alu155)+127)<<23)))));
      float alu230 = ((alu8<-150.0f)?0.0f:alu229);
      float alu231 = (((alu14<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu204)+0.001339262701f)*alu204)+0.009618384764f)*alu204)+0.05550347269f)*alu204)+0.2402264476f)*alu204)+0.6931471825f)*alu204)+1.0f)*__builtin_bit_cast(float, (int)(((alu157+127)<<23)))*__builtin_bit_cast(float, (int)((((cast2-alu157)+127)<<23)))));
      float alu232 = ((alu14<-150.0f)?0.0f:alu231);
      float alu233 = (((alu20<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu205)+0.001339262701f)*alu205)+0.009618384764f)*alu205)+0.05550347269f)*alu205)+0.2402264476f)*alu205)+0.6931471825f)*alu205)+1.0f)*__builtin_bit_cast(float, (int)(((alu159+127)<<23)))*__builtin_bit_cast(float, (int)((((cast3-alu159)+127)<<23)))));
      float alu234 = ((alu20<-150.0f)?0.0f:alu233);
      float alu235 = (((alu26<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu206)+0.001339262701f)*alu206)+0.009618384764f)*alu206)+0.05550347269f)*alu206)+0.2402264476f)*alu206)+0.6931471825f)*alu206)+1.0f)*__builtin_bit_cast(float, (int)(((alu161+127)<<23)))*__builtin_bit_cast(float, (int)((((cast4-alu161)+127)<<23)))));
      float alu236 = ((alu26<-150.0f)?0.0f:alu235);
      float alu237 = (((alu32<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu207)+0.001339262701f)*alu207)+0.009618384764f)*alu207)+0.05550347269f)*alu207)+0.2402264476f)*alu207)+0.6931471825f)*alu207)+1.0f)*__builtin_bit_cast(float, (int)(((alu163+127)<<23)))*__builtin_bit_cast(float, (int)((((cast5-alu163)+127)<<23)))));
      float alu238 = ((alu32<-150.0f)?0.0f:alu237);
      float alu239 = (((alu38<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu208)+0.001339262701f)*alu208)+0.009618384764f)*alu208)+0.05550347269f)*alu208)+0.2402264476f)*alu208)+0.6931471825f)*alu208)+1.0f)*__builtin_bit_cast(float, (int)(((alu165+127)<<23)))*__builtin_bit_cast(float, (int)((((cast6-alu165)+127)<<23)))));
      float alu240 = ((alu38<-150.0f)?0.0f:alu239);
      float alu241 = (((alu44<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu209)+0.001339262701f)*alu209)+0.009618384764f)*alu209)+0.05550347269f)*alu209)+0.2402264476f)*alu209)+0.6931471825f)*alu209)+1.0f)*__builtin_bit_cast(float, (int)(((alu167+127)<<23)))*__builtin_bit_cast(float, (int)((((cast7-alu167)+127)<<23)))));
      float alu242 = ((alu44<-150.0f)?0.0f:alu241);
      float alu243 = (((alu50<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu210)+0.001339262701f)*alu210)+0.009618384764f)*alu210)+0.05550347269f)*alu210)+0.2402264476f)*alu210)+0.6931471825f)*alu210)+1.0f)*__builtin_bit_cast(float, (int)(((alu169+127)<<23)))*__builtin_bit_cast(float, (int)((((cast8-alu169)+127)<<23)))));
      float alu244 = ((alu50<-150.0f)?0.0f:alu243);
      float alu245 = (((alu56<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu211)+0.001339262701f)*alu211)+0.009618384764f)*alu211)+0.05550347269f)*alu211)+0.2402264476f)*alu211)+0.6931471825f)*alu211)+1.0f)*__builtin_bit_cast(float, (int)(((alu171+127)<<23)))*__builtin_bit_cast(float, (int)((((cast9-alu171)+127)<<23)))));
      float alu246 = ((alu56<-150.0f)?0.0f:alu245);
      float alu247 = (((alu62<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu212)+0.001339262701f)*alu212)+0.009618384764f)*alu212)+0.05550347269f)*alu212)+0.2402264476f)*alu212)+0.6931471825f)*alu212)+1.0f)*__builtin_bit_cast(float, (int)(((alu173+127)<<23)))*__builtin_bit_cast(float, (int)((((cast10-alu173)+127)<<23)))));
      float alu248 = ((alu62<-150.0f)?0.0f:alu247);
      float alu249 = (((alu68<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu213)+0.001339262701f)*alu213)+0.009618384764f)*alu213)+0.05550347269f)*alu213)+0.2402264476f)*alu213)+0.6931471825f)*alu213)+1.0f)*__builtin_bit_cast(float, (int)(((alu175+127)<<23)))*__builtin_bit_cast(float, (int)((((cast11-alu175)+127)<<23)))));
      float alu250 = ((alu68<-150.0f)?0.0f:alu249);
      float alu251 = (((alu74<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu214)+0.001339262701f)*alu214)+0.009618384764f)*alu214)+0.05550347269f)*alu214)+0.2402264476f)*alu214)+0.6931471825f)*alu214)+1.0f)*__builtin_bit_cast(float, (int)(((alu177+127)<<23)))*__builtin_bit_cast(float, (int)((((cast12-alu177)+127)<<23)))));
      float alu252 = ((alu74<-150.0f)?0.0f:alu251);
      float alu253 = (((alu80<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu215)+0.001339262701f)*alu215)+0.009618384764f)*alu215)+0.05550347269f)*alu215)+0.2402264476f)*alu215)+0.6931471825f)*alu215)+1.0f)*__builtin_bit_cast(float, (int)(((alu179+127)<<23)))*__builtin_bit_cast(float, (int)((((cast13-alu179)+127)<<23)))));
      float alu254 = ((alu80<-150.0f)?0.0f:alu253);
      float alu255 = (((alu86<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu216)+0.001339262701f)*alu216)+0.009618384764f)*alu216)+0.05550347269f)*alu216)+0.2402264476f)*alu216)+0.6931471825f)*alu216)+1.0f)*__builtin_bit_cast(float, (int)(((alu181+127)<<23)))*__builtin_bit_cast(float, (int)((((cast14-alu181)+127)<<23)))));
      float alu256 = ((alu86<-150.0f)?0.0f:alu255);
      float alu257 = (((alu92<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu217)+0.001339262701f)*alu217)+0.009618384764f)*alu217)+0.05550347269f)*alu217)+0.2402264476f)*alu217)+0.6931471825f)*alu217)+1.0f)*__builtin_bit_cast(float, (int)(((alu183+127)<<23)))*__builtin_bit_cast(float, (int)((((cast15-alu183)+127)<<23)))));
      float alu258 = ((alu92<-150.0f)?0.0f:alu257);
      float alu259 = (((alu98<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu218)+0.001339262701f)*alu218)+0.009618384764f)*alu218)+0.05550347269f)*alu218)+0.2402264476f)*alu218)+0.6931471825f)*alu218)+1.0f)*__builtin_bit_cast(float, (int)(((alu185+127)<<23)))*__builtin_bit_cast(float, (int)((((cast16-alu185)+127)<<23)))));
      float alu260 = ((alu98<-150.0f)?0.0f:alu259);
      float alu261 = (((alu104<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu219)+0.001339262701f)*alu219)+0.009618384764f)*alu219)+0.05550347269f)*alu219)+0.2402264476f)*alu219)+0.6931471825f)*alu219)+1.0f)*__builtin_bit_cast(float, (int)(((alu187+127)<<23)))*__builtin_bit_cast(float, (int)((((cast17-alu187)+127)<<23)))));
      float alu262 = ((alu104<-150.0f)?0.0f:alu261);
      float alu263 = (((alu110<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu220)+0.001339262701f)*alu220)+0.009618384764f)*alu220)+0.05550347269f)*alu220)+0.2402264476f)*alu220)+0.6931471825f)*alu220)+1.0f)*__builtin_bit_cast(float, (int)(((alu189+127)<<23)))*__builtin_bit_cast(float, (int)((((cast18-alu189)+127)<<23)))));
      float alu264 = ((alu110<-150.0f)?0.0f:alu263);
      float alu265 = (((alu116<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu221)+0.001339262701f)*alu221)+0.009618384764f)*alu221)+0.05550347269f)*alu221)+0.2402264476f)*alu221)+0.6931471825f)*alu221)+1.0f)*__builtin_bit_cast(float, (int)(((alu191+127)<<23)))*__builtin_bit_cast(float, (int)((((cast19-alu191)+127)<<23)))));
      float alu266 = ((alu116<-150.0f)?0.0f:alu265);
      float alu267 = (((alu122<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu222)+0.001339262701f)*alu222)+0.009618384764f)*alu222)+0.05550347269f)*alu222)+0.2402264476f)*alu222)+0.6931471825f)*alu222)+1.0f)*__builtin_bit_cast(float, (int)(((alu193+127)<<23)))*__builtin_bit_cast(float, (int)((((cast20-alu193)+127)<<23)))));
      float alu268 = ((alu122<-150.0f)?0.0f:alu267);
      float alu269 = (((alu128<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu223)+0.001339262701f)*alu223)+0.009618384764f)*alu223)+0.05550347269f)*alu223)+0.2402264476f)*alu223)+0.6931471825f)*alu223)+1.0f)*__builtin_bit_cast(float, (int)(((alu195+127)<<23)))*__builtin_bit_cast(float, (int)((((cast21-alu195)+127)<<23)))));
      float alu270 = ((alu128<-150.0f)?0.0f:alu269);
      float alu271 = (((alu134<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu224)+0.001339262701f)*alu224)+0.009618384764f)*alu224)+0.05550347269f)*alu224)+0.2402264476f)*alu224)+0.6931471825f)*alu224)+1.0f)*__builtin_bit_cast(float, (int)(((alu197+127)<<23)))*__builtin_bit_cast(float, (int)((((cast22-alu197)+127)<<23)))));
      float alu272 = ((alu134<-150.0f)?0.0f:alu271);
      float alu273 = (((alu140<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu225)+0.001339262701f)*alu225)+0.009618384764f)*alu225)+0.05550347269f)*alu225)+0.2402264476f)*alu225)+0.6931471825f)*alu225)+1.0f)*__builtin_bit_cast(float, (int)(((alu199+127)<<23)))*__builtin_bit_cast(float, (int)((((cast23-alu199)+127)<<23)))));
      float alu274 = ((alu140<-150.0f)?0.0f:alu273);
      float alu275 = (((alu146<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu226)+0.001339262701f)*alu226)+0.009618384764f)*alu226)+0.05550347269f)*alu226)+0.2402264476f)*alu226)+0.6931471825f)*alu226)+1.0f)*__builtin_bit_cast(float, (int)(((alu201+127)<<23)))*__builtin_bit_cast(float, (int)((((cast24-alu201)+127)<<23)))));
      float alu276 = ((alu146<-150.0f)?0.0f:alu275);
      float alu277 = (alu3?((float)(__builtin_nanf(""))):alu228);
      float alu278 = (alu9?((float)(__builtin_nanf(""))):alu230);
      float alu279 = (alu15?((float)(__builtin_nanf(""))):alu232);
      float alu280 = (alu21?((float)(__builtin_nanf(""))):alu234);
      float alu281 = (alu27?((float)(__builtin_nanf(""))):alu236);
      float alu282 = (alu33?((float)(__builtin_nanf(""))):alu238);
      float alu283 = (alu39?((float)(__builtin_nanf(""))):alu240);
      float alu284 = (alu45?((float)(__builtin_nanf(""))):alu242);
      float alu285 = (alu51?((float)(__builtin_nanf(""))):alu244);
      float alu286 = (alu57?((float)(__builtin_nanf(""))):alu246);
      float alu287 = (alu63?((float)(__builtin_nanf(""))):alu248);
      float alu288 = (alu69?((float)(__builtin_nanf(""))):alu250);
      float alu289 = (alu75?((float)(__builtin_nanf(""))):alu252);
      float alu290 = (alu81?((float)(__builtin_nanf(""))):alu254);
      float alu291 = (alu87?((float)(__builtin_nanf(""))):alu256);
      float alu292 = (alu93?((float)(__builtin_nanf(""))):alu258);
      float alu293 = (alu99?((float)(__builtin_nanf(""))):alu260);
      float alu294 = (alu105?((float)(__builtin_nanf(""))):alu262);
      float alu295 = (alu111?((float)(__builtin_nanf(""))):alu264);
      float alu296 = (alu117?((float)(__builtin_nanf(""))):alu266);
      float alu297 = (alu123?((float)(__builtin_nanf(""))):alu268);
      float alu298 = (alu129?((float)(__builtin_nanf(""))):alu270);
      float alu299 = (alu135?((float)(__builtin_nanf(""))):alu272);
      float alu300 = (alu141?((float)(__builtin_nanf(""))):alu274);
      float alu301 = (alu147?((float)(__builtin_nanf(""))):alu276);
      for (int Lidx3 = 0; Lidx3 < 4; Lidx3++) {
        int alu302 = (Lidx3<<2);
        int alu303 = ((Lidx1<<4)+alu302);
        float4 val27 = (*((float4*)((data4_1600+(alu303+64)))));
        float4 val28 = (*((float4*)((data4_1600+(alu303+128)))));
        float4 val29 = (*((float4*)((data4_1600+(alu303+192)))));
        float4 val30 = (*((float4*)((data4_1600+(alu303+256)))));
        float4 val31 = (*((float4*)((data4_1600+(alu303+320)))));
        float4 val32 = (*((float4*)((data4_1600+(alu303+384)))));
        float4 val33 = (*((float4*)((data4_1600+(alu303+448)))));
        float4 val34 = (*((float4*)((data4_1600+(alu303+512)))));
        float4 val35 = (*((float4*)((data4_1600+(alu303+576)))));
        float4 val36 = (*((float4*)((data4_1600+(alu303+640)))));
        float4 val37 = (*((float4*)((data4_1600+(alu303+704)))));
        float4 val38 = (*((float4*)((data4_1600+(alu303+768)))));
        float4 val39 = (*((float4*)((data4_1600+(alu303+832)))));
        float4 val40 = (*((float4*)((data4_1600+(alu303+896)))));
        float4 val41 = (*((float4*)((data4_1600+(alu303+960)))));
        float4 val42 = (*((float4*)((data4_1600+(alu303+1024)))));
        float4 val43 = (*((float4*)((data4_1600+(alu303+1088)))));
        float4 val44 = (*((float4*)((data4_1600+(alu303+1152)))));
        float4 val45 = (*((float4*)((data4_1600+(alu303+1216)))));
        float4 val46 = (*((float4*)((data4_1600+(alu303+1280)))));
        float4 val47 = (*((float4*)((data4_1600+(alu303+1344)))));
        float4 val48 = (*((float4*)((data4_1600+(alu303+1408)))));
        float4 val49 = (*((float4*)((data4_1600+(alu303+1472)))));
        float4 val50 = (*((float4*)((data4_1600+(alu303+1536)))));
        float4 val51 = (*((float4*)((data4_1600+alu303))));
        *((float4*)((data0_1600+((Lidx2<<4)+alu302+(Lidx1*400))))) = (float4){(((alu301*val51[0])+(alu277*val27[0])+(alu278*val28[0])+(alu279*val29[0])+(alu280*val30[0])+(alu281*val31[0])+(alu282*val32[0])+(alu283*val33[0])+(alu284*val34[0])+(alu285*val35[0])+(alu286*val36[0])+(alu287*val37[0])+(alu288*val38[0])+(alu289*val39[0])+(alu290*val40[0])+(alu291*val41[0])+(alu292*val42[0])+(alu293*val43[0])+(alu294*val44[0])+(alu295*val45[0])+(alu296*val46[0])+(alu297*val47[0])+(alu298*val48[0])+(alu299*val49[0])+(alu300*val50[0]))*val26),(((alu301*val51[1])+(alu277*val27[1])+(alu278*val28[1])+(alu279*val29[1])+(alu280*val30[1])+(alu281*val31[1])+(alu282*val32[1])+(alu283*val33[1])+(alu284*val34[1])+(alu285*val35[1])+(alu286*val36[1])+(alu287*val37[1])+(alu288*val38[1])+(alu289*val39[1])+(alu290*val40[1])+(alu291*val41[1])+(alu292*val42[1])+(alu293*val43[1])+(alu294*val44[1])+(alu295*val45[1])+(alu296*val46[1])+(alu297*val47[1])+(alu298*val48[1])+(alu299*val49[1])+(alu300*val50[1]))*val26),(((alu301*val51[2])+(alu277*val27[2])+(alu278*val28[2])+(alu279*val29[2])+(alu280*val30[2])+(alu281*val31[2])+(alu282*val32[2])+(alu283*val33[2])+(alu284*val34[2])+(alu285*val35[2])+(alu286*val36[2])+(alu287*val37[2])+(alu288*val38[2])+(alu289*val39[2])+(alu290*val40[2])+(alu291*val41[2])+(alu292*val42[2])+(alu293*val43[2])+(alu294*val44[2])+(alu295*val45[2])+(alu296*val46[2])+(alu297*val47[2])+(alu298*val48[2])+(alu299*val49[2])+(alu300*val50[2]))*val26),(((alu301*val51[3])+(alu277*val27[3])+(alu278*val28[3])+(alu279*val29[3])+(alu280*val30[3])+(alu281*val31[3])+(alu282*val32[3])+(alu283*val33[3])+(alu284*val34[3])+(alu285*val35[3])+(alu286*val36[3])+(alu287*val37[3])+(alu288*val38[3])+(alu289*val39[3])+(alu290*val40[3])+(alu291*val41[3])+(alu292*val42[3])+(alu293*val43[3])+(alu294*val44[3])+(alu295*val45[3])+(alu296*val46[3])+(alu297*val47[3])+(alu298*val48[3])+(alu299*val49[3])+(alu300*val50[3]))*val26)};
      }
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4_4_16n2(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_1600, float* restrict data3_4096, float* restrict data4_64) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 16; Lidx2++) {
      int alu0 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0_0 = 0; Ridx0_0 < 4; Ridx0_0++) {
        int alu5 = ((Ridx0_0*400)+(Lidx1<<4));
        float4 val0 = (*((float4*)((data2_1600+alu5))));
        int alu6 = ((Ridx0_0<<10)+alu0);
        float4 val1 = (*((float4*)((data3_4096+(alu6+64)))));
        float4 val2 = (*((float4*)((data3_4096+(alu6+128)))));
        float4 val3 = (*((float4*)((data3_4096+(alu6+192)))));
        float4 val4 = (*((float4*)((data3_4096+(alu6+960)))));
        float4 val5 = (*((float4*)((data3_4096+alu6))));
        float4 val6 = (*((float4*)((data2_1600+(alu5+4)))));
        float4 val7 = (*((float4*)((data3_4096+(alu6+256)))));
        float4 val8 = (*((float4*)((data3_4096+(alu6+320)))));
        float4 val9 = (*((float4*)((data3_4096+(alu6+384)))));
        float4 val10 = (*((float4*)((data3_4096+(alu6+448)))));
        float4 val11 = (*((float4*)((data2_1600+(alu5+8)))));
        float4 val12 = (*((float4*)((data3_4096+(alu6+512)))));
        float4 val13 = (*((float4*)((data3_4096+(alu6+576)))));
        float4 val14 = (*((float4*)((data3_4096+(alu6+640)))));
        float4 val15 = (*((float4*)((data3_4096+(alu6+704)))));
        float4 val16 = (*((float4*)((data2_1600+(alu5+12)))));
        float4 val17 = (*((float4*)((data3_4096+(alu6+768)))));
        float4 val18 = (*((float4*)((data3_4096+(alu6+832)))));
        float4 val19 = (*((float4*)((data3_4096+(alu6+896)))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val5[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0])+(val6[0]*val7[0])+(val6[1]*val8[0])+(val6[2]*val9[0])+(val6[3]*val10[0])+(val11[0]*val12[0])+(val11[1]*val13[0])+(val11[2]*val14[0])+(val11[3]*val15[0])+(val16[0]*val17[0])+(val16[1]*val18[0])+(val16[2]*val19[0])+(val16[3]*val4[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val5[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1])+(val6[0]*val7[1])+(val6[1]*val8[1])+(val6[2]*val9[1])+(val6[3]*val10[1])+(val11[0]*val12[1])+(val11[1]*val13[1])+(val11[2]*val14[1])+(val11[3]*val15[1])+(val16[0]*val17[1])+(val16[1]*val18[1])+(val16[2]*val19[1])+(val16[3]*val4[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val5[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2])+(val6[0]*val7[2])+(val6[1]*val8[2])+(val6[2]*val9[2])+(val6[3]*val10[2])+(val11[0]*val12[2])+(val11[1]*val13[2])+(val11[2]*val14[2])+(val11[3]*val15[2])+(val16[0]*val17[2])+(val16[1]*val18[2])+(val16[2]*val19[2])+(val16[3]*val4[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val5[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3])+(val6[0]*val7[3])+(val6[1]*val8[3])+(val6[2]*val9[3])+(val6[3]*val10[3])+(val11[0]*val12[3])+(val11[1]*val13[3])+(val11[2]*val14[3])+(val11[3]*val15[3])+(val16[0]*val17[3])+(val16[1]*val18[3])+(val16[2]*val19[3])+(val16[3]*val4[3]));
      }
      int alu12 = ((Lidx1<<6)+alu0);
      float4 val20 = (*((float4*)((data1_1600+alu12))));
      float4 val21 = (*((float4*)((data4_64+alu0))));
      *((float4*)((data0_1600+alu12))) = (float4){(val20[0]+(*(acc0+0))+val21[0]),(val20[1]+(*(acc0+1))+val21[1]),(val20[2]+(*(acc0+2))+val21[2]),(val20[3]+(*(acc0+3))+val21[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4n8(float* restrict data0_25, float* restrict data1_1600) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
      *(acc0+0) = ((*(acc0+0))+val0[0]+val0[1]+val0[2]+val0[3]);
    }
    *(data0_25+Lidx1) = ((*(acc0+0))*0.015625f);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4n9(float* restrict data0_25, float* restrict data1_1600, float* restrict data2_25) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    float val0 = (*(data2_25+Lidx1));
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val1 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
      float alu1 = (val1[0]-val0);
      float alu2 = (val1[1]-val0);
      float alu3 = (val1[2]-val0);
      float alu4 = (val1[3]-val0);
      *(acc0+0) = ((*(acc0+0))+(alu1*alu1)+(alu2*alu2)+(alu3*alu3)+(alu4*alu4));
    }
    *(data0_25+Lidx1) = (1.0f/__builtin_sqrtf((((*(acc0+0))*0.015625f)+1e-05f)));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_E_25_16_4n4(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_25, float* restrict data3_25, float* restrict data4_64, float* restrict data5_64) {
  for (int Lidx0 = 0; Lidx0 < 25; Lidx0++) {
    float val0 = (*(data2_25+Lidx0));
    float val1 = (*(data3_25+Lidx0));
    for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
      int alu0 = (Lidx1<<2);
      int alu1 = ((Lidx0<<6)+alu0);
      float4 val2 = (*((float4*)((data1_1600+alu1))));
      float4 val3 = (*((float4*)((data4_64+alu0))));
      float4 val4 = (*((float4*)((data5_64+alu0))));
      *((float4*)((data0_1600+alu1))) = (float4){(((val2[0]-val0)*val1*val3[0])+val4[0]),(((val2[1]-val0)*val1*val3[1])+val4[1]),(((val2[2]-val0)*val1*val3[2])+val4[2]),(((val2[3]-val0)*val1*val3[3])+val4[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_32_4_16_4n2(float* restrict data0_3200, float* restrict data1_1600, float* restrict data2_8192, float* restrict data3_128) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 32; Lidx2++) {
      int alu0 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
        float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
        int alu5 = ((Ridx0<<9)+alu0);
        float4 val1 = (*((float4*)((data2_8192+(alu5+128)))));
        float4 val2 = (*((float4*)((data2_8192+(alu5+256)))));
        float4 val3 = (*((float4*)((data2_8192+(alu5+384)))));
        float4 val4 = (*((float4*)((data2_8192+alu5))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val4[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val4[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val4[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val4[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3]));
      }
      float4 val5 = (*((float4*)((data3_128+alu0))));
      float alu11 = ((*(acc0+0))+val5[0]);
      float alu12 = ((*(acc0+1))+val5[1]);
      float alu13 = ((*(acc0+2))+val5[2]);
      float alu14 = ((*(acc0+3))+val5[3]);
      float alu15 = ((0.0f<alu11)?alu11:0.0f);
      float alu16 = ((0.0f<alu12)?alu12:0.0f);
      float alu17 = ((0.0f<alu13)?alu13:0.0f);
      float alu18 = ((0.0f<alu14)?alu14:0.0f);
      *((float4*)((data0_3200+((Lidx1<<7)+alu0)))) = (float4){alu15,alu16,alu17,alu18};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4_32_4n2(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_3200, float* restrict data3_8192, float* restrict data4_64) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 16; Lidx2++) {
      int alu0 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 32; Ridx0++) {
        float4 val0 = (*((float4*)((data2_3200+((Ridx0<<2)+(Lidx1<<7))))));
        int alu5 = ((Ridx0<<8)+alu0);
        float4 val1 = (*((float4*)((data3_8192+(alu5+64)))));
        float4 val2 = (*((float4*)((data3_8192+(alu5+128)))));
        float4 val3 = (*((float4*)((data3_8192+(alu5+192)))));
        float4 val4 = (*((float4*)((data3_8192+alu5))));
        *(acc0+0) = ((*(acc0+0))+(val0[0]*val4[0])+(val0[1]*val1[0])+(val0[2]*val2[0])+(val0[3]*val3[0]));
        *(acc0+1) = ((*(acc0+1))+(val0[0]*val4[1])+(val0[1]*val1[1])+(val0[2]*val2[1])+(val0[3]*val3[1]));
        *(acc0+2) = ((*(acc0+2))+(val0[0]*val4[2])+(val0[1]*val1[2])+(val0[2]*val2[2])+(val0[3]*val3[2]));
        *(acc0+3) = ((*(acc0+3))+(val0[0]*val4[3])+(val0[1]*val1[3])+(val0[2]*val2[3])+(val0[3]*val3[3]));
      }
      int alu11 = ((Lidx1<<6)+alu0);
      float4 val5 = (*((float4*)((data1_1600+alu11))));
      float4 val6 = (*((float4*)((data4_64+alu0))));
      *((float4*)((data0_1600+alu11))) = (float4){(val5[0]+(*(acc0+0))+val6[0]),(val5[1]+(*(acc0+1))+val6[1]),(val5[2]+(*(acc0+2))+val6[2]),(val5[3]+(*(acc0+3))+val6[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4n10(float* restrict data0_25, float* restrict data1_1600) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val0 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
      *(acc0+0) = ((*(acc0+0))+val0[0]+val0[1]+val0[2]+val0[3]);
    }
    *(data0_25+Lidx1) = ((*(acc0+0))*0.015625f);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_25_16_4n11(float* restrict data0_25, float* restrict data1_1600, float* restrict data2_25) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 25; Lidx1++) {
    float val0 = (*(data2_25+Lidx1));
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val1 = (*((float4*)((data1_1600+((Ridx0<<2)+(Lidx1<<6))))));
      float alu1 = (val1[0]-val0);
      float alu2 = (val1[1]-val0);
      float alu3 = (val1[2]-val0);
      float alu4 = (val1[3]-val0);
      *(acc0+0) = ((*(acc0+0))+(alu1*alu1)+(alu2*alu2)+(alu3*alu3)+(alu4*alu4));
    }
    *(data0_25+Lidx1) = (1.0f/__builtin_sqrtf((((*(acc0+0))*0.015625f)+1e-05f)));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_E_25_16_4n5(float* restrict data0_1600, float* restrict data1_1600, float* restrict data2_25, float* restrict data3_25, float* restrict data4_64, float* restrict data5_64) {
  for (int Lidx0 = 0; Lidx0 < 25; Lidx0++) {
    float val0 = (*(data2_25+Lidx0));
    float val1 = (*(data3_25+Lidx0));
    for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
      int alu0 = (Lidx1<<2);
      int alu1 = ((Lidx0<<6)+alu0);
      float4 val2 = (*((float4*)((data1_1600+alu1))));
      float4 val3 = (*((float4*)((data4_64+alu0))));
      float4 val4 = (*((float4*)((data5_64+alu0))));
      *((float4*)((data0_1600+alu1))) = (float4){(((val2[0]-val0)*val1*val3[0])+val4[0]),(((val2[1]-val0)*val1*val3[1])+val4[1]),(((val2[2]-val0)*val1*val3[2])+val4[2]),(((val2[3]-val0)*val1*val3[3])+val4[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_201_25n1(float* restrict data0_201, float* restrict data1_1600, float* restrict data2_24, float* restrict data3_1, float* restrict data4_73) {
  float val0 = (*(data3_1+0));
  float4 val1 = (*((float4*)((data2_24+0))));
  float4 val2 = (*((float4*)((data2_24+4))));
  float4 val3 = (*((float4*)((data2_24+8))));
  float4 val4 = (*((float4*)((data2_24+12))));
  float4 val5 = (*((float4*)((data2_24+16))));
  float4 val6 = (*((float4*)((data2_24+20))));
  for (int Lidx1 = 0; Lidx1 < 201; Lidx1++) {
    _Bool alu0 = ((63<Lidx1)&(Lidx1<128));
    float val7 = (alu0?*(data1_1600+(Lidx1+-64)):0.0f);
    float val8 = (alu0?*(data1_1600+(Lidx1+64)):0.0f);
    float val9 = (alu0?*(data1_1600+(Lidx1+128)):0.0f);
    float val10 = (alu0?*(data1_1600+(Lidx1+192)):0.0f);
    float val11 = (alu0?*(data1_1600+(Lidx1+256)):0.0f);
    float val12 = (alu0?*(data1_1600+(Lidx1+320)):0.0f);
    float val13 = (alu0?*(data1_1600+(Lidx1+384)):0.0f);
    float val14 = (alu0?*(data1_1600+(Lidx1+448)):0.0f);
    float val15 = (alu0?*(data1_1600+(Lidx1+512)):0.0f);
    float val16 = (alu0?*(data1_1600+(Lidx1+576)):0.0f);
    float val17 = (alu0?*(data1_1600+(Lidx1+640)):0.0f);
    float val18 = (alu0?*(data1_1600+(Lidx1+704)):0.0f);
    float val19 = (alu0?*(data1_1600+(Lidx1+768)):0.0f);
    float val20 = (alu0?*(data1_1600+(Lidx1+832)):0.0f);
    float val21 = (alu0?*(data1_1600+(Lidx1+896)):0.0f);
    float val22 = (alu0?*(data1_1600+(Lidx1+960)):0.0f);
    float val23 = (alu0?*(data1_1600+(Lidx1+1024)):0.0f);
    float val24 = (alu0?*(data1_1600+(Lidx1+1088)):0.0f);
    float val25 = (alu0?*(data1_1600+(Lidx1+1152)):0.0f);
    float val26 = (alu0?*(data1_1600+(Lidx1+1216)):0.0f);
    float val27 = (alu0?*(data1_1600+(Lidx1+1280)):0.0f);
    float val28 = (alu0?*(data1_1600+(Lidx1+1344)):0.0f);
    float val29 = (alu0?*(data1_1600+(Lidx1+1408)):0.0f);
    float val30 = (alu0?*(data1_1600+(Lidx1+1472)):0.0f);
    float val31 = ((Lidx1<64)?*(data1_1600+Lidx1):0.0f);
    float val32 = (alu0?*(data1_1600+Lidx1):0.0f);
    float val33 = ((127<Lidx1)?*(data4_73+(Lidx1+-128)):0.0f);
    float alu1 = (alu0?((val7+(val32*val1[0])+(val8*val1[1])+(val9*val1[2])+(val10*val1[3])+(val11*val2[0])+(val12*val2[1])+(val13*val2[2])+(val14*val2[3])+(val15*val3[0])+(val16*val3[1])+(val17*val3[2])+(val18*val3[3])+(val19*val4[0])+(val20*val4[1])+(val21*val4[2])+(val22*val4[3])+(val23*val5[0])+(val24*val5[1])+(val25*val5[2])+(val26*val5[3])+(val27*val6[0])+(val28*val6[1])+(val29*val6[2])+(val30*val6[3]))/val0):0.0f);
    *(data0_201+Lidx1) = (val31+alu1+val33);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_64_4_201n1(float* restrict data0_256, float* restrict data1_201, float* restrict data2_51456, float* restrict data3_256) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 64; Lidx1++) {
    int alu0 = (Lidx1<<2);
    *(acc0+0) = 0.0f;
    *(acc0+1) = 0.0f;
    *(acc0+2) = 0.0f;
    *(acc0+3) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 201; Ridx0++) {
      float val0 = (*(data1_201+Ridx0));
      float4 val1 = (*((float4*)((data2_51456+((Ridx0<<8)+alu0)))));
      *(acc0+0) = ((*(acc0+0))+(val0*val1[0]));
      *(acc0+1) = ((*(acc0+1))+(val0*val1[1]));
      *(acc0+2) = ((*(acc0+2))+(val0*val1[2]));
      *(acc0+3) = ((*(acc0+3))+(val0*val1[3]));
    }
    float4 val2 = (*((float4*)((data3_256+alu0))));
    float alu10 = ((*(acc0+0))+val2[0]);
    float alu11 = ((*(acc0+1))+val2[1]);
    float alu12 = ((*(acc0+2))+val2[2]);
    float alu13 = ((*(acc0+3))+val2[3]);
    float alu14 = ((0.0f<alu10)?alu10:0.0f);
    float alu15 = ((0.0f<alu11)?alu11:0.0f);
    float alu16 = ((0.0f<alu12)?alu12:0.0f);
    float alu17 = ((0.0f<alu13)?alu13:0.0f);
    *((float4*)((data0_256+alu0))) = (float4){alu14,alu15,alu16,alu17};
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_96_64_4n1(float* restrict data0_96, float* restrict data1_256, float* restrict data2_24576, float* restrict data3_96) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 96; Lidx1++) {
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 64; Ridx0++) {
      int alu1 = ((Ridx0*384)+Lidx1);
      float val0 = (*(data2_24576+(alu1+96)));
      float val1 = (*(data2_24576+(alu1+192)));
      float val2 = (*(data2_24576+(alu1+288)));
      float val3 = (*(data2_24576+alu1));
      float4 val4 = (*((float4*)((data1_256+(Ridx0<<2)))));
      *(acc0+0) = ((*(acc0+0))+(val4[0]*val3)+(val4[1]*val0)+(val4[2]*val1)+(val4[3]*val2));
    }
    float val5 = (*(data3_96+Lidx1));
    *(data0_96+Lidx1) = ((*(acc0+0))+val5);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_context_r_96_16_4n1(float* restrict data0_1, float* restrict data1_96, float* restrict data2_6144, float* restrict data3_64, float* restrict data4_64, float* restrict data5_1) {
  float acc0[4];
  float acc1[1];
  *(acc1+0) = 0.0f;
  for (int Ridx1 = 0; Ridx1 < 16; Ridx1++) {
    int alu1 = (Ridx1<<2);
    *(acc0+0) = 0.0f;
    *(acc0+1) = 0.0f;
    *(acc0+2) = 0.0f;
    *(acc0+3) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 96; Ridx0++) {
      float val0 = (*(data1_96+Ridx0));
      float4 val1 = (*((float4*)((data2_6144+((Ridx0<<6)+alu1)))));
      *(acc0+0) = ((*(acc0+0))+(val0*val1[0]));
      *(acc0+1) = ((*(acc0+1))+(val0*val1[1]));
      *(acc0+2) = ((*(acc0+2))+(val0*val1[2]));
      *(acc0+3) = ((*(acc0+3))+(val0*val1[3]));
    }
    float4 val2 = (*((float4*)((data3_64+alu1))));
    float4 val3 = (*((float4*)((data4_64+alu1))));
    float alu11 = ((*(acc0+0))+val2[0]);
    float alu12 = ((0.0f<alu11)?alu11:0.0f);
    float alu13 = ((*(acc0+1))+val2[1]);
    float alu14 = ((*(acc0+2))+val2[2]);
    float alu15 = ((*(acc0+3))+val2[3]);
    float alu16 = ((0.0f<alu13)?alu13:0.0f);
    float alu17 = ((0.0f<alu14)?alu14:0.0f);
    float alu18 = ((0.0f<alu15)?alu15:0.0f);
    *(acc1+0) = ((*(acc1+0))+(alu12*val3[0])+(alu16*val3[1])+(alu17*val3[2])+(alu18*val3[3]));
  }
  float val4 = (*(data5_1+0));
  *(data0_1+0) = ((*(acc1+0))+val4);
}

void* jepa_context_bufs[49];
void jepa_context_set_buf(size_t index, void* ptr) {
  jepa_context_bufs[index] = ptr;
}
float jepa_context_buf_12[1600];
float jepa_context_buf_26[100];
float jepa_context_buf_54[201];
float jepa_context_buf_10[25];
float jepa_context_buf_31[3200];
float jepa_context_buf_11[25];
float jepa_context_buf_24[2500];
float jepa_context_buf_15[1600];
float jepa_context_buf_4[1];
float jepa_context_buf_0[888];
float jepa_context_buf_25[100];
float jepa_context_buf_18[1600];
float jepa_context_buf_21[1600];
float jepa_context_buf_55[256];
float jepa_context_buf_5[1600];
void jepa_context_net(float* output0,float* output1,float* output2,float* output3,float* output4,float* output5,float* input0,int* input1,float* input2,float* input3)
{
  jepa_context_E_24_37n1(jepa_context_buf_0, input2, input1, (float *)jepa_context_bufs[0], (float *)jepa_context_bufs[1], (float *)jepa_context_bufs[2]);
  jepa_context_r_25n1(jepa_context_buf_4, input3);
  jepa_context_r_25_16_4_73_37n1(jepa_context_buf_5, input0, (float *)jepa_context_bufs[3], (float *)jepa_context_bufs[4], jepa_context_buf_0, (float *)jepa_context_bufs[5], (float *)jepa_context_bufs[6]);
  jepa_context_r_25_16_4n2(jepa_context_buf_10, jepa_context_buf_5);
  jepa_context_r_25_16_4n3(jepa_context_buf_11, jepa_context_buf_5, jepa_context_buf_10);
  jepa_context_E_25_16_4n1(jepa_context_buf_12, jepa_context_buf_5, jepa_context_buf_10, jepa_context_buf_11, (float *)jepa_context_bufs[7], (float *)jepa_context_bufs[8]);
  jepa_context_r_25_16_4_16_4n1(jepa_context_buf_15, jepa_context_buf_12, (float *)jepa_context_bufs[9], (float *)jepa_context_bufs[10]);
  jepa_context_r_25_16_4_16_4n2(jepa_context_buf_18, jepa_context_buf_12, (float *)jepa_context_bufs[11], (float *)jepa_context_bufs[12]);
  jepa_context_r_25_16_4_16_4n3(jepa_context_buf_21, jepa_context_buf_12, (float *)jepa_context_bufs[13], (float *)jepa_context_bufs[14]);
  jepa_context_r_25_25_4_16n1(jepa_context_buf_24, jepa_context_buf_15, jepa_context_buf_18, input3);
  jepa_context_E_4_25_4_4n1(output1, jepa_context_buf_18);
  jepa_context_E_4_25_4_4n2(output2, jepa_context_buf_21);
  jepa_context_r_100_25n2(jepa_context_buf_25, jepa_context_buf_24);
  jepa_context_r_100_25n3(jepa_context_buf_26, jepa_context_buf_24, jepa_context_buf_25);
  jepa_context_r_4_25_4_4_25n1(jepa_context_buf_12, jepa_context_buf_24, jepa_context_buf_25, jepa_context_buf_26, jepa_context_buf_21);
  jepa_context_r_25_16_4_4_16n1(jepa_context_buf_15, jepa_context_buf_5, jepa_context_buf_12, (float *)jepa_context_bufs[15], (float *)jepa_context_bufs[16]);
  jepa_context_r_25_16_4n4(jepa_context_buf_10, jepa_context_buf_15);
  jepa_context_r_25_16_4n5(jepa_context_buf_11, jepa_context_buf_15, jepa_context_buf_10);
  jepa_context_E_25_16_4n2(jepa_context_buf_5, jepa_context_buf_15, jepa_context_buf_10, jepa_context_buf_11, (float *)jepa_context_bufs[17], (float *)jepa_context_bufs[18]);
  jepa_context_r_25_32_4_16_4n1(jepa_context_buf_31, jepa_context_buf_5, (float *)jepa_context_bufs[19], (float *)jepa_context_bufs[20]);
  jepa_context_r_25_16_4_32_4n1(jepa_context_buf_5, jepa_context_buf_15, jepa_context_buf_31, (float *)jepa_context_bufs[21], (float *)jepa_context_bufs[22]);
  jepa_context_r_25_16_4n6(jepa_context_buf_10, jepa_context_buf_5);
  jepa_context_r_25_16_4n7(jepa_context_buf_11, jepa_context_buf_5, jepa_context_buf_10);
  jepa_context_E_25_16_4n3(jepa_context_buf_12, jepa_context_buf_5, jepa_context_buf_10, jepa_context_buf_11, (float *)jepa_context_bufs[23], (float *)jepa_context_bufs[24]);
  jepa_context_r_25_16_4_16_4n4(jepa_context_buf_15, jepa_context_buf_12, (float *)jepa_context_bufs[25], (float *)jepa_context_bufs[26]);
  jepa_context_r_25_16_4_16_4n5(jepa_context_buf_18, jepa_context_buf_12, (float *)jepa_context_bufs[27], (float *)jepa_context_bufs[28]);
  jepa_context_r_25_16_4_16_4n6(jepa_context_buf_21, jepa_context_buf_12, (float *)jepa_context_bufs[29], (float *)jepa_context_bufs[30]);
  jepa_context_r_25_25_4_16n2(jepa_context_buf_24, jepa_context_buf_15, jepa_context_buf_18, input3);
  jepa_context_E_4_25_4_4n3(output3, jepa_context_buf_18);
  jepa_context_E_4_25_4_4n4(output4, jepa_context_buf_21);
  jepa_context_r_100_25n4(jepa_context_buf_25, jepa_context_buf_24);
  jepa_context_r_100_25n5(jepa_context_buf_26, jepa_context_buf_24, jepa_context_buf_25);
  jepa_context_r_4_25_4_4_25n2(jepa_context_buf_12, jepa_context_buf_24, jepa_context_buf_25, jepa_context_buf_26, jepa_context_buf_21);
  jepa_context_r_25_16_4_4_16n2(jepa_context_buf_15, jepa_context_buf_5, jepa_context_buf_12, (float *)jepa_context_bufs[31], (float *)jepa_context_bufs[32]);
  jepa_context_r_25_16_4n8(jepa_context_buf_10, jepa_context_buf_15);
  jepa_context_r_25_16_4n9(jepa_context_buf_11, jepa_context_buf_15, jepa_context_buf_10);
  jepa_context_E_25_16_4n4(jepa_context_buf_5, jepa_context_buf_15, jepa_context_buf_10, jepa_context_buf_11, (float *)jepa_context_bufs[33], (float *)jepa_context_bufs[34]);
  jepa_context_r_25_32_4_16_4n2(jepa_context_buf_31, jepa_context_buf_5, (float *)jepa_context_bufs[35], (float *)jepa_context_bufs[36]);
  jepa_context_r_25_16_4_32_4n2(jepa_context_buf_5, jepa_context_buf_15, jepa_context_buf_31, (float *)jepa_context_bufs[37], (float *)jepa_context_bufs[38]);
  jepa_context_r_25_16_4n10(jepa_context_buf_10, jepa_context_buf_5);
  jepa_context_r_25_16_4n11(jepa_context_buf_11, jepa_context_buf_5, jepa_context_buf_10);
  jepa_context_E_25_16_4n5(jepa_context_buf_12, jepa_context_buf_5, jepa_context_buf_10, jepa_context_buf_11, (float *)jepa_context_bufs[39], (float *)jepa_context_bufs[40]);
  jepa_context_r_201_25n1(jepa_context_buf_54, jepa_context_buf_12, input3, jepa_context_buf_4, input0);
  jepa_context_r_64_4_201n1(jepa_context_buf_55, jepa_context_buf_54, (float *)jepa_context_bufs[41], (float *)jepa_context_bufs[42]);
  jepa_context_r_96_64_4n1(output0, jepa_context_buf_55, (float *)jepa_context_bufs[43], (float *)jepa_context_bufs[44]);
  jepa_context_r_96_16_4n1(output5, output0, (float *)jepa_context_bufs[45], (float *)jepa_context_bufs[46], (float *)jepa_context_bufs[47], (float *)jepa_context_bufs[48]);
}