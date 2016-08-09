/***************************  REQUIRED LIBRARIES  ***************************/

#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <getopt.h>

#include <gsl/gsl_rng.h>
#include <gsl/gsl_randist.h>

#include "LPF.h"
#include "BayesLine.h"
#include "Subroutines.h"
#include "LISAPathfinder.h"
#include "TimePhaseMaximization.h"

/* ============================  MAIN PROGRAM  ============================ */

void parse(int argc, char **argv, struct Data *data, struct Flags *flags);

static void print_usage() {
  printf("\n");
  printf("Usage: \n");
  printf("REQUIRED:\n");
  printf("  -d | --dof     : degrees of freedom (3 or 6) \n");
  printf("  -n | --nseed   : seed for noise simulation \n");
  printf("  -s | --seed    : seed for MCMC \n");
  printf("DATA HANDLING:\n");
  printf("       --simdata : use simulated data (default)\n");
  printf("       --datapath: path to directory with data files\n");
  printf("       --trigtime: GPS start time of data segment\n");
  printf("       --duration: duration of data segment\n");
  printf("OPTIONAL:\n");
  printf("  -i | --iseed   : seed for injection/data RNG (def. same as noise) \n");
  printf("  -f | --fixd    : fixed dimension (no RJ)  \n");
  printf("  -h | --help    : usage information        \n");
  printf("  -p | --prior   : sample prior             \n");
  printf("  -v | --verbose : enable verbose output    \n");
  printf("  -j | --johns   : turn off John's LPF model\n");

  printf("EXAMPLE:\n");
  printf("./mcmc --dof 6 --seed 1234 --nseed 1234\n");
  printf("\n");
  exit(EXIT_FAILURE);
}


int main(int argc, char **argv)
{

  /* bail gracefully if no arguments given */
  if(argc==0)print_usage();

  /* declare variables */
  int i,j,k,ic,n,mc;
  int accept;
  int MCMCSTEPS;
  int BURNIN;
  int NC;
  int nmax=12;
  int n_hidden_steps=10;

  double H;
  double alpha;

  char filename[128];

  /* Structure for run flags */
  struct Flags *flags = malloc(sizeof(struct Flags));

  /* Initialize spacecraft structure */
  struct Spacecraft *lpf = malloc(sizeof(struct Spacecraft));

  initialize_spacecraft(lpf);

  // Spacecraft mass
  lpf->M = EOM_SC_M;

  // Housing 1 Geometry
  lpf->RTM[0][0] = EOM_H1SC_X;
  lpf->RTM[0][1] = EOM_H1SC_Y;
  lpf->RTM[0][2] = EOM_H1SC_Z;
  // Housing 2 Geometry
  lpf->RTM[1][0] = EOM_H2SC_X;
  lpf->RTM[1][1] = EOM_H2SC_Y;
  lpf->RTM[1][2] = EOM_H2SC_Z;

  // COM Geometry
  lpf->RB[0] = EOM_RB_X;
  lpf->RB[1] = EOM_RB_Y;
  lpf->RB[2] = EOM_RB_Z;

  // Spacecraft Geometry
  lpf->x[0][0] = SC_BOT_CORNER_6_X;
  lpf->x[0][1] = SC_BOT_CORNER_6_Y;
  lpf->x[1][0] = SC_BOT_CORNER_5_X;
  lpf->x[1][1] = SC_BOT_CORNER_5_Y;
  lpf->x[2][0] = SC_BOT_CORNER_4_X;
  lpf->x[2][1] = SC_BOT_CORNER_4_Y;
  lpf->x[3][0] = SC_BOT_CORNER_3_X;
  lpf->x[3][1] = SC_BOT_CORNER_3_Y;
  lpf->x[4][0] = SC_BOT_CORNER_2_X;
  lpf->x[4][1] = SC_BOT_CORNER_2_Y;
  lpf->x[5][0] = SC_BOT_CORNER_1_X;
  lpf->x[5][1] = SC_BOT_CORNER_1_Y;
  lpf->x[6][0] = SC_BOT_CORNER_8_X;
  lpf->x[6][1] = SC_BOT_CORNER_8_Y;
  lpf->x[7][0] = SC_BOT_CORNER_7_X;
  lpf->x[7][1] = SC_BOT_CORNER_7_Y;
  lpf->x[8][0] = SC_BOT_CORNER_6_X;
  lpf->x[8][1] = SC_BOT_CORNER_6_Y;

  // Spacecraft dimensions
  lpf->H = SC_H;
  lpf->W = lpf->x[0][0] - lpf->x[4][0];
  lpf->D = lpf->x[2][1] - lpf->x[6][1];

  // Moment of inertia about H1
  lpf->I[0][0][0] = EOM_SC_IH1_XX;
  lpf->I[0][0][1] = EOM_SC_IH1_XY;
  lpf->I[0][0][2] = EOM_SC_IH1_XZ;

  lpf->I[0][1][0] = EOM_SC_IH1_YX;
  lpf->I[0][1][1] = EOM_SC_IH1_YY;
  lpf->I[0][1][2] = EOM_SC_IH1_YZ;

  lpf->I[0][2][0] = EOM_SC_IH1_ZX;
  lpf->I[0][2][1] = EOM_SC_IH1_ZY;
  lpf->I[0][2][2] = EOM_SC_IH1_ZZ;

  // Moment of inertia about H2
  lpf->I[1][0][0] = EOM_SC_IH2_XX;
  lpf->I[1][0][1] = EOM_SC_IH2_XY;
  lpf->I[1][0][2] = EOM_SC_IH2_XZ;

  lpf->I[1][1][0] = EOM_SC_IH2_YX;
  lpf->I[1][1][1] = EOM_SC_IH2_YY;
  lpf->I[1][1][2] = EOM_SC_IH2_YZ;

  lpf->I[1][2][0] = EOM_SC_IH2_ZX;
  lpf->I[1][2][1] = EOM_SC_IH2_ZY;
  lpf->I[1][2][2] = EOM_SC_IH2_ZZ;

  matrix_invert(lpf->I[0], lpf->invI[0], 3);
  matrix_invert(lpf->I[1], lpf->invI[1], 3);


  /* Initialize data structure */
  struct Data  *data = malloc(sizeof(struct Data));


  parse(argc, argv, data, flags);

  data->T  = 16384.0;
  data->dt = 1.0;//0.4;
  data->df = 1.0/data->T;
  data->N  = (int)(data->T/data->dt)/2;

  data->fmin = data->df; //Hz
  data->fmax = (double)data->N/data->T;  //Hz

  data->imin = (int)floor(data->fmin*data->T);
  data->imax = (int)floor(data->fmax*data->T);

  data->d = malloc(data->DOF*sizeof(double *));
  data->s = malloc(data->DOF*sizeof(double *));
  data->n = malloc(data->DOF*sizeof(double *));

  for(i=0; i<data->DOF; i++)
  {
    data->d[i] = malloc(data->N*2*sizeof(double));
    data->s[i] = malloc(data->N*2*sizeof(double));
    data->n[i] = malloc(data->N*2*sizeof(double));
  }

  data->f = malloc(data->N*sizeof(double));

  /* set up GSL random number generators */
  const gsl_rng_type *T = gsl_rng_default;

  gsl_rng *ir = gsl_rng_alloc (T);
  gsl_rng *nr = gsl_rng_alloc (T);
  gsl_rng *r  = gsl_rng_alloc (T);
  gsl_rng_env_setup();
  gsl_rng_set (r, data->seed);
  gsl_rng_set (nr, data->nseed);
  gsl_rng_set (ir, data->iseed);

  
  /* Dump info on faces */
  FILE *facefile = fopen("faces.dat","w");
  write_faces(facefile,lpf);
  fclose(facefile);

  /* Initialize parallel chains */
  NC = 10;
  int *index = malloc(NC*sizeof(double));
  double *temp = malloc(NC*sizeof(double));
  double dT = 1.5;
  temp[0] = 1.0;
  index[0]=0;
  for(ic=1; ic<NC; ic++)
  {
    temp[ic]=temp[ic-1]*dT;
    index[ic]=ic;
  }
  temp[NC-1]=1.e6;

  /* Simulate noise data */
  struct Model *injection = malloc(sizeof(struct Model));
  struct Model **model = malloc(NC*sizeof(struct Model*));
  struct Model *trial  = malloc(sizeof(struct Model));
  initialize_model(trial, data->N, nmax, data->DOF);
  initialize_model(injection,data->N,6, data->DOF);

  struct BayesLineParams ***bayesline = malloc(NC*sizeof(struct BayesLineParams **));


  for(ic=0; ic<NC; ic++)
  {
    model[ic] = malloc(sizeof(struct Model));
    initialize_model(model[ic],data->N,nmax, data->DOF);
  }



  int im,re;
  int N=data->N;


  for(i=0; i<3; i++)
  {
    injection->Ais[i] = NOISE_GRS_POS;
    injection->Ath[i] = NOISE_COLD_GAS;
    injection->Ars[i] = NOISE_GRS_ANG;
  }

  /* Simulate source data */
  struct Source *source;

  injection->N = 1;
  for(n=0; n<injection->N; n++)
  {
    source = injection->source[n];
    source->face = -1;
    if(flags->use_spacecraft==0)while(source->face ==-1) draw_impact_point(data, lpf, source, ir);
    else while(source->face ==-1) draw_impact_point_sc(data, lpf, source, ir);
    draw_impactor(data, source, r);
    source->P = 10000;
    //source->P = 1;//    ***************************************           hack to test the prior without signal
    printf("hit on face %i\n",source->face);
  }

  if(flags->simdata)
  {
    simulate_noise(data, lpf, injection, nr);
    //int k;for(i=0; i<2*data->N; i++)for(k=0; k<data->DOF; k++)data->n[k][i]=0;//    ************* hack to test the prior without noise
    simulate_data(data);
    simulate_injection(data,lpf,injection);
    Sn(data, lpf, injection, injection->Snf);
  }
  //Read in LPF data
  else
  {
    FILE **dfptr = malloc(data->DOF*sizeof(FILE *));
    sprintf(filename,"%s/g1_x_%s_%s.txt",    data->path,data->gps,data->duration);
    dfptr[0] = fopen(filename,"r");
    sprintf(filename,"%s/g1_y_%s_%s.txt",    data->path,data->gps,data->duration);
    dfptr[1] = fopen(filename,"r");
    sprintf(filename,"%s/g1_z_%s_%s.txt",    data->path,data->gps,data->duration);
    dfptr[2] = fopen(filename,"r");
    sprintf(filename,"%s/g1_theta_%s_%s.txt",data->path,data->gps,data->duration);
    dfptr[3] = fopen(filename,"r");
    sprintf(filename,"%s/g1_eta_%s_%s.txt",  data->path,data->gps,data->duration);
    dfptr[4] = fopen(filename,"r");
    sprintf(filename,"%s/g1_phi_%s_%s.txt",  data->path,data->gps,data->duration);
    dfptr[5] = fopen(filename,"r");
    for(k=0; k<data->DOF; k++)
    {
      for(i=0; i<N; i++)
      {
        re = 2*i;
        im = re+1;
        fscanf(dfptr[k],"%lg %lg %lg",&data->f[i], &data->d[k][re], &data->d[k][im]);
        data->f[i] -= 1./data->T;
      }
      fclose(dfptr[k]);
    }
    
    /* Read in spacecraft mass properties */
    sprintf(filename,"%s/g1_mass_props_%s_%s.txt",data->path,data->gps,data->duration);
    FILE *mfptr = fopen(filename,"r");
    char line[1024];
    
    // S/C Mass Properties used for g1 segment with t0 = 1140854817
    fgets(line,1024,mfptr);
    
    // SC mass (kg)
    fgets(line,1024,mfptr);
    fscanf(mfptr,"%lg",&lpf->M);
    
    // SC center of mass in mechanical frame (x,y,z) in meters
    fgets(line,1024,mfptr);
    fscanf(mfptr,"%lg %lg %lg",&lpf->RB[0],&lpf->RB[1],&lpf->RB[2]);

    // SC moment of inertia in body frame in kg-m^2
    fgets(line,1024,mfptr);
    fgets(line,1024,mfptr);//unused
    fgets(line,1024,mfptr);//unused
    fgets(line,1024,mfptr);//unused
    
    // SC moment of inertia in H1 frame in kg-m^2
    fgets(line,1024,mfptr);
    fscanf(mfptr,"%lg %lg %lg",&lpf->I[0][0][0],&lpf->I[0][0][1],&lpf->I[0][0][2]);
    fscanf(mfptr,"%lg %lg %lg",&lpf->I[0][1][0],&lpf->I[0][1][1],&lpf->I[0][1][2]);
    fscanf(mfptr,"%lg %lg %lg",&lpf->I[0][2][0],&lpf->I[0][2][1],&lpf->I[0][2][2]);
    
    // SC moment of inertia in H2 frame in kg-m^2
    fgets(line,1024,mfptr);
    fscanf(mfptr,"%lg %lg %lg",&lpf->I[1][0][0],&lpf->I[1][0][1],&lpf->I[1][0][2]);
    fscanf(mfptr,"%lg %lg %lg",&lpf->I[1][1][0],&lpf->I[1][1][1],&lpf->I[1][1][2]);
    fscanf(mfptr,"%lg %lg %lg",&lpf->I[1][2][0],&lpf->I[1][2][1],&lpf->I[1][2][2]);

    
    fclose(mfptr);

    /* Set up BayesLine model */
    fprintf(stdout,"\n ============ BayesLine ==============\n");

    /*
     Setup BayesLine structure
     */
    for(ic=0; ic<NC; ic++)
    {
      bayesline[ic] = malloc(data->DOF*sizeof(struct BayesLineParams *));
      initialize_bayesline(bayesline[ic], data, model[ic]->Snf);
    }

    int NI=data->DOF;
    for(k=0; k<NI; k++)
    {

      for(i=0; i<N; i++)
      {
        bayesline[0][k]->power[i] = (data->d[k][2*i]*data->d[k][2*i]+data->d[k][2*i+1]*data->d[k][2*i+1]);
      }

      //TODO: Is passing d(f) to BayesLineSearch etc. redundant?
      fprintf(stdout,"BayesLine search phase for IFO %i\n", k);
      BayesLineSearch(bayesline[0][k], data->d[k], data->fmin, data->fmax, data->dt, data->T);

      fprintf(stdout,"BayesLine characterization phase for IFO %i\n", k);
      BayesLineRJMCMC(bayesline[0][k], data->d[k], model[0]->Snf[k], model[0]->invSnf[k], model[0]->SnS[k], 2*N, 1000, 1.0, 0);

      for(i=0; i<N; i++)
      {
        model[0]->Snf[k][i]*=2.0;
        model[0]->SnS[k][i] = model[0]->Snf[k][i];
        model[0]->invSnf[k][i] = 1./model[0]->Snf[k][i];
        injection->Snf[k][i]=model[0]->Snf[k][i];
      }
    }

    //        //Start PSD off at reference from BayesLine
    //        dfptr[0] = fopen("/Users/tyson/Research/LISAPathfinder/run_20160429/01/x/fullspectrum_pdf.dat","r");
    //        dfptr[1] = fopen("/Users/tyson/Research/LISAPathfinder/run_20160429/01/y/fullspectrum_pdf.dat","r");
    //        dfptr[2] = fopen("/Users/tyson/Research/LISAPathfinder/run_20160429/01/z/fullspectrum_pdf.dat","r");
    //        dfptr[3] = fopen("/Users/tyson/Research/LISAPathfinder/run_20160429/01/theta/fullspectrum_pdf.dat","r");
    //        dfptr[4] = fopen("/Users/tyson/Research/LISAPathfinder/run_20160429/01/eta/fullspectrum_pdf.dat","r");
    //        dfptr[5] = fopen("/Users/tyson/Research/LISAPathfinder/run_20160429/01/phi/fullspectrum_pdf.dat","r");
    //        int count;
    //        double junk;
    //        for(k=0; k<data->DOF; k++)
    //        {
    //            count=0;
    //            while(!feof(dfptr[k]))
    //            {
    //                re = count*i;
    //                im = re+1;
    //                fscanf(dfptr[k],"%lg %lg %lg %lg %lg %lg %lg",&junk,&junk,&junk,&junk,&junk,&junk,&injection->Snf[k][count]);
    //                count++;
    //            }
    //            count--;
    //            for(i=count; i<N; i++)
    //            {
    //                injection->Snf[k][i] = injection->Snf[k][count-1];
    //            }
    //            fclose(dfptr[k]);
    //        }
    free(dfptr);
  }

  injection->logL = loglikelihood(data, lpf, injection, flags);

  printf("Injected parameters:   \n");
  FILE *injfile = fopen("injection.dat","w");
  for(n=0; n<injection->N; n++)printf("     {%lg,%lg,%lg,%lg,%lg,%lg,%lg,%lg,%lg}\n"              ,injection->source[n]->t0, injection->source[n]->P, injection->source[n]->costheta, injection->source[n]->phi, injection->source[n]->map[0], injection->source[n]->map[1], injection->source[n]->r[0], injection->source[n]->r[1], injection->source[n]->r[2]);
  for(n=0; n<injection->N; n++)fprintf(injfile,"%lg %lg %lg %lg %lg %lg %lg %lg %lg\n",injection->source[n]->t0, injection->source[n]->P, injection->source[n]->costheta, injection->source[n]->phi, injection->source[n]->map[0], injection->source[n]->map[1], injection->source[n]->r[0], injection->source[n]->r[1], injection->source[n]->r[2]);

  fclose(injfile);
  printf("SNR of injection = %g\n",snr(data, lpf, injection));

  //    /* Initialize parallel chains */
  //    NC = 15;
  //    int *index = malloc(NC*sizeof(double));
  //    double *temp = malloc(NC*sizeof(double));
  //    double dT = 1.5;
  //    temp[0] = 1.0;
  //    index[0]=0;
  //    for(ic=1; ic<NC; ic++)
  //    {
  //        temp[ic]=temp[ic-1]*dT;
  //        index[ic]=ic;
  //    }
  //    temp[NC-1]=1.e6;

  //    /* Initialize model */
  //    struct Model **model = malloc(NC*sizeof(struct Model*));
  //
  //    struct Model *trial  = malloc(sizeof(struct Model));
  //    initialize_model(trial, data->N, nmax, data->DOF);


  for(ic=0; ic<NC; ic++)
  {
    //        model[ic] = malloc(sizeof(struct Model));
    //        initialize_model(model[ic],data->N,nmax, data->DOF);

    copy_model(injection, model[ic], data->N, data->DOF);

    detector_proposal(data,injection,model[ic],r);

    for(n=0; n<model[ic]->N; n++)
    {
      model[ic]->source[n]->P  = gsl_ran_exponential(r,10000.);
      model[ic]->source[n]->t0 = gsl_rng_uniform(r)*data->T;

    }
    int *drew_prior=malloc(nmax*sizeof(int));
    for(i=0;i<nmax;i++)drew_prior[i]=1;
    if(flags->use_spacecraft==0)logprior(data, model[ic], injection);
    else logprior_sc(data, lpf, model[ic], injection,drew_prior);
    //Sn(data, lpf, model[ic], model[ic]->Snf);

    for(i=0; i<N; i++)
    {
      for(k=0; k<data->DOF; k++)
      {
        model[ic]->Snf[k][i] = injection->Snf[k][i];
      }
    }

    model[ic]->logL = loglikelihood(data, lpf, model[ic], flags);

    free(drew_prior);
  }

  //    /* Set up BayesLine model */
  //    struct BayesLineParams ***bayesline = malloc(NC*sizeof(struct BayesLineParams **));
  //    fprintf(stdout,"\n ============ BayesLine ==============\n");
  //
  //    /*
  //     Setup BayesLine structure
  //     */
  //    for(ic=0; ic<NC; ic++)
  //    {
  //        bayesline[ic] = malloc(data->DOF*sizeof(struct BayesLineParams *));
  //        initialize_bayesline(bayesline[ic], data, model[ic]->Snf);
  //    }
  //
  //    int ifo;
  //    int imin=data->imin;
  //    int imax=data->imax;
  //    int NI=data->DOF;
  //      for(ifo=0; ifo<NI; ifo++)
  //      {
  //
  //        for(i=0; i<N; i++)
  //        {
  //          bayesline[0][ifo]->power[i] = (data->d[ifo][2*i]*data->d[ifo][2*i]+data->d[ifo][2*i+1]*data->d[ifo][2*i+1]);
  //        }
  //
  //        //TODO: Is passing d(f) to BayesLineSearch etc. redundant?
  //        fprintf(stdout,"BayesLine search phase for IFO %i\n", ifo);
  //        BayesLineSearch(bayesline[0][ifo], data->d[ifo], data->fmin, data->fmax, data->dt, data->T);
  //
  //        fprintf(stdout,"BayesLine characterization phase for IFO %i\n", ifo);
  //        BayesLineRJMCMC(bayesline[0][ifo], data->d[ifo], model[0]->Snf[ifo], model[0]->invSnf[ifo], model[0]->SnS[ifo], 2*N, 1000, 1.0, 0);
  //
  //        for(i=0; i<N; i++)
  //        {
  //          model[0]->Snf[ifo][i]*=2.0;
  //          model[0]->SnS[ifo][i] = model[0]->Snf[ifo][i];
  //          model[0]->invSnf[ifo][i] = 1./model[0]->Snf[ifo][i];
  //        }
  //      }

  model[0]->logL = loglikelihood(data, lpf, model[0], flags);

  for(ic=1; ic<NC; ic++)
  {
    for(k=0; k<data->DOF; k++)
    {
      for(i=0; i<N; i++)
      {
        model[ic]->Snf[k][i]    = model[0]->Snf[k][i];
        model[ic]->SnS[k][i]    = model[0]->Snf[k][i];
        model[ic]->invSnf[k][i] = model[0]->invSnf[k][i];
      }
      copy_bayesline_params(bayesline[0][k], bayesline[ic][k]);
    }
    model[ic]->logL = loglikelihood(data, lpf, model[ic], flags);

  }

  FILE *fptr=fopen("temp.dat","w");
  for(i=data->imin; i<data->imax; i++)
  {
    fprintf(fptr,"%lg ",(double)i/data->T);
    for(k=0; k<data->DOF; k++)
    {
      fprintf(fptr,"%lg %lg ", bayesline[0][k]->power[i], model[0]->Snf[k][i]);
    }
    fprintf(fptr,"\n");
  }
  fclose(fptr);

  for(i=0; i<data->DOF; i++)
  {
    sprintf(filename,"TD_data_%i.dat",i);
    //void print_time_domain_waveforms(char filename[], double *h, int N, double *Snf, double eta, double Tobs, int imin, int imax, double tmin, double tmax)
    printf("T=%g, imin=%i, imax=%i, N=%i\n", data->T, data->imin, data->imax, data->N);
    print_time_domain_waveforms(filename, data->d[i], data->N*2, model[0]->Snf[i], 1.0, data->T, data->imin, data->imax, 0.0, data->T);

  }

  /* set up distribution */
  //struct PSDposterior *psd = NULL;
  //setup_psd_histogram(data, injection, psd);

  /* set up MCMC run */
  accept    = 0;
  MCMCSTEPS = 100000;
  BURNIN    = MCMCSTEPS/100;//1000;

  FILE *noisechain;
  sprintf(filename,"noisechain.dat");
  noisechain = fopen(filename,"w");
  //fprintf(noisechain,"#dlogL mass dAi[x] dAth[x] dAi[y] dAth[y] dAi[z] dAth[z]\n");

  FILE *impactchain;
  sprintf(filename,"impactchain.dat");
  impactchain = fopen(filename,"w");
  //fprintf(impactchain,"#dlogL N t0[0] P[0] costheta[0] phi[0] ... \n");

  FILE *logLchain;
  sprintf(filename,"logLchain.dat");
  logLchain = fopen(filename,"w");
  //fprintf(logLchain,"#dlogL[0] dlogL[1] ... T[0] T[1]...\n");

  int reject;

  /* Here is the MCMC loop */
  int step=MCMCSTEPS/100;
  FILE *psdfile=NULL;
  for(mc=0;mc<MCMCSTEPS;mc++)
  {
    for(ic=0; ic<NC; ic++)
    {
      int *drew_impact_from_prior=malloc(nmax*sizeof(int));

      for(n=0; n<n_hidden_steps; n++)
      {
        trial->logQ = model[index[ic]]->logQ = 0.0;
        reject=0;

        //copy x to y
        copy_model(model[index[ic]], trial, data->N, data->DOF);

        //choose new parameters for y
        proposal(flags, data, lpf, model[index[ic]], trial, r, &reject, nmax, drew_impact_from_prior);

        //compute maximized likelihood
        //if(mc<BURNIN) max_loglikelihood(data, trial);
        if(reject) continue;
        else
        {
          //compute new likelihood
          trial->logL = loglikelihood(data, lpf, trial, flags);

          //compute new prior
          if(flags->use_spacecraft==0)
            logprior(data, trial, injection);
          else
          {
            logprior_sc(data, lpf, trial, injection, drew_impact_from_prior);
            logprior_sc(data, lpf, model[index[ic]], injection, drew_impact_from_prior);
          }
          if(model[index[ic]]->N==trial->N)
          {
            for(i=0; i<model[index[ic]]->N; i++)
              model[index[ic]]->logP += log(gsl_ran_exponential_pdf(model[index[ic]]->source[i]->P,10000));
            for(i=0; i<trial->N; i++)
              trial->logP += log(gsl_ran_exponential_pdf(trial->source[i]->P,10000));
          }
          else
          {
            //TODO: HACK priors in RJ Hasting's ratio--only OK because the birth move exclusively draws from prior
            model[index[ic]]->logP = trial->logP = 0.0;
          }

          //compute Hastings ratio
          //if(model[index[ic]]->logP<-1e59) continue;
          //else
          H     = (trial->logL - model[index[ic]]->logL)/temp[ic] + trial->logP - model[index[ic]]->logP;// - trial->logQ + model[index[ic]]->logQ;
          //if(model[index[ic]]->N!=trial->N)printf("%i->%i:  H = %g + %g - %g - %g + %g-> %g\n",model[index[ic]]->N,trial->N,(trial->logL - model[index[ic]]->logL)/temp[index[ic]],trial->logP, model[index[ic]]->logP,trial->logQ , model[index[ic]]->logQ,H);
          alpha = log(gsl_rng_uniform(r));

          //          if(ic==0 && trial->source[0]->face==1)printf("H=%g, logLy=%g, logLx=%g\n",H,trial->logL,model[index[ic]]->logL);

          //adopt new position w/ probability H
          if(H>alpha)
          {
            copy_model(trial, model[index[ic]], data->N, data->DOF);
            accept++;
          }
        }//Metropolis-Hastings
      }//Loop over inter-model updates
      free(drew_impact_from_prior);

    }//Loop over chains
    
    for(ic=0; ic<NC; ic++)
    {
      bayesline_mcmc(data, model, bayesline, index, 1., ic);
      model[index[ic]]->logL = loglikelihood(data, lpf, model[index[ic]], flags);
    }
    
    ptmcmc(model, temp, index, r, NC, mc);

    //cute PSD histogram
    //if(mc>MCMCSTEPS/2) populate_psd_histogram(data, model[index[0]], MCMCSTEPS, psd);

    //print chain files

    //impact parameters
    ic = index[0];
    fprintf(noisechain,"%lg ",model[ic]->logL-injection->logL);
    //fprintf(noisechain,"%lg ",model[ic]->mass);
    for(i=0; i<3; i++)
    {
      fprintf(noisechain,"%lg %lg %lg ",(injection->Ais[i]-model[ic]->Ais[i])/injection->Ais[i],(injection->Ath[i]-model[ic]->Ath[i])/injection->Ath[i],(injection->Ars[i]-model[ic]->Ars[i])/injection->Ars[i]);
    }
    fprintf(noisechain,"\n");

    for(n=0; n<model[ic]->N; n++)
    {
      source = model[ic]->source[n];
      //printf(".");
      //check_source_incidence(lpf,source,n);
      if(flags->use_spacecraft==0){
        face2map(lpf, source->r,source->map);
        which_face_r(source->r);
      } else {
        int iface=source->face;
        body2face(lpf, iface, source->r,source->map);
      }
      fprintf(impactchain,"%lg ",model[ic]->logL-injection->logL);
      fprintf(impactchain,"%i ",model[ic]->N);
      fprintf(impactchain,"%lg %lg %lg %lg %lg %lg %i %lg %lg %lg\n", source->t0,source->P,source->map[0], source->map[1], source->costheta,source->phi,source->face, source->r[0], source->r[1], source->r[2]);
    }fflush(impactchain);

    if(flags->verbose)
    {
      for(n=0; n<model[ic]->N; n++)
      {
        source = model[ic]->source[n];

        fprintf(stdout,"%lg ",model[ic]->logL-injection->logL);
        fprintf(stdout,"%i ",model[ic]->N);
        fprintf(stdout,"%lg %lg %lg %lg %lg %lg %i %lg %lg %lg\n", source->t0,source->P,source->map[0], source->map[1], source->costheta,source->phi,source->face, source->r[0], source->r[1], source->r[2]);
      }
    }

    //parallel tempering
    fprintf(logLchain,"%i ",model[index[0]]->N);
    for(ic=0; ic<NC; ic++) fprintf(logLchain,"%lg ",model[index[ic]]->logL-injection->logL);
    for(ic=0; ic<NC; ic++) fprintf(logLchain,"%lg ",temp[ic]);
    fprintf(logLchain,"\n");


    if(mc%step==0)
    {
      sprintf(filename,"psd.dat.%i",mc/step);
      psdfile=fopen(filename,"w");
      for(i=0; i<N; i++)
      {
        fprintf(psdfile,"%lg ",(double)i/data->T);
        for(k=0; k<data->DOF; k++)
        {
          fprintf(psdfile,"%lg ",model[index[0]]->Snf[k][i]);
        }
        fprintf(psdfile,"\n");
      }
      fclose(psdfile);
    }


    //peak at current model
    if(mc%100==0)
    {
      double **h=malloc(data->DOF*sizeof(double *));
      for(i=0; i<data->DOF; i++)
      {
        h[i]=malloc(data->N*2*sizeof(double));
        for(j=0; j<data->N*2; j++) h[i][j]=0.0;
      }

      for(i=0; i<model[index[0]]->N; i++)
      {
        LPFImpulseResponse(model[index[0]]->s, data, lpf, model[index[0]]->source[i]);
        for(j=0; j<data->DOF; j++)
        {
          for(k=0; k<data->N*2; k++) h[j][k]+=model[index[0]]->s[j][k];
        }
      }
      for(i=0; i<data->DOF; i++)
      {
        sprintf(filename,"TD_model_%i.dat",i);
        print_time_domain_waveforms(filename, h[i], data->N*2, model[index[0]]->Snf[i], 1.0, data->T, data->imin, data->imax, 0.0, data->T);
      }
      for(i=0; i<data->DOF; i++)
      {
        free(h[i]);
      }
      free(h);

    }


    //if(mc%100)printf("finished round %i/%i\n",mc,MCMCSTEPS);
  }//MCMC
  printf("acceptance rate = %g\n",(double)accept/(double)MCMCSTEPS);


  //  FILE *PSDfile = fopen("psdhistogram.dat","w");
  //  for(i=0; i<psd->Nx; i++)
  //  {
  //    for(j=0; j<psd->Ny; j++)
  //    {
  //      fprintf(PSDfile,"%lg %lg %lg\n",psd->xmin + i*psd->dx, psd->ymin + j*psd->dy, psd->histogram[i][j]);
  //    }
  //  }
  //  fclose(PSDfile);

  return 0;
}



void parse(int argc, char **argv, struct Data *data, struct Flags *flags)
{
  data->DOF = 6;
  data->seed  = 1234;
  data->nseed = 1234;
  data->iseed = -1;
  flags->verbose = 0;
  flags->prior = 0;
  flags->rj = 1;
  flags->use_spacecraft = 1;  //set to 1 for John's treatment of spacecraft surface structure

  static int simdata = 0;

  if(argc==1) print_usage();

  //Specifying the expected options
  static struct option long_options[] = {

    /* These options set a flag. */
    {"simdata", no_argument, &simdata, 1},
    {"datapath",required_argument, 0, 0},
    {"trigtime",required_argument, 0, 0},
    {"duration",required_argument, 0, 0},

    /* These options don’t set a flag.
     We distinguish them by their indices. */
    {"dof",     required_argument, 0,  'd' },
    {"fixd",    no_argument,       0,  'f' },
    {"help",    no_argument,       0,  'h' },
    {"nseed",   required_argument, 0,  'n' },
    {"seed",    required_argument, 0,  's' },
    {"iseed",   required_argument, 0,  'i' },
    {"verbose", no_argument,       0,  'v' },
    {"prior",   no_argument,       0,  'p' },
    {"johns",   no_argument,       0,  'j' },
    {0,         0,                 0,   0  }
  };

  int opt=0;
  int long_index =0;

  //Print command line
  FILE *out = fopen("mcmc.sh","w");
  fprintf(out,"#!/bin/sh\n\n");
  for(opt=0; opt<argc; opt++) fprintf(out,"%s ",argv[opt]);
  fprintf(out,"\n\n");
  fclose(out);

  //Loop through argv string and pluck out arguments
  while ((opt = getopt_long_only(argc, argv,"apl:b:",
                                 long_options, &long_index )) != -1) {
    switch (opt) {

      case 0:
        /* If this option set a flag, do nothing else now. */
        //              if (long_options[long_index].flag != 0)
        //              {
        //                  printf("setting flag %s to %i\n",long_options[long_index].name,simdata);
        //                  break;
        //              }
        //              printf ("option %s", long_options[long_index].name);
        //              if (optarg)
        //                  printf (" with arg %s", optarg);
        //              printf ("\n");
        if(strcmp("datapath",long_options[long_index].name) == 0) sprintf(data->path,    "%s",optarg);
        if(strcmp("trigtime",long_options[long_index].name) == 0) sprintf(data->gps,     "%s",optarg);
        if(strcmp("duration",long_options[long_index].name) == 0) sprintf(data->duration,"%s",optarg);
        break;


      case 'd' : data->DOF = atoi(optarg);
        break;
      case 'f' : flags->rj = 0;
        break;
      case 'h' :
        print_usage();
        exit(EXIT_FAILURE);
        break;
      case 'p' : flags->prior = 1;
        break;
      case 'n' : data->nseed = atoi(optarg);
        break;
      case 's' : data->seed = atoi(optarg);
        break;
      case 'i' : data->iseed = atoi(optarg);
        break;
      case 'v' : flags->verbose = 1;
        break;
      case 'j' : flags->use_spacecraft = 0;
        break;
      default: print_usage();
        exit(EXIT_FAILURE);
    }
  }

  // set flags
  flags->simdata  = (int)simdata;

  // make sense of arguments
  int abort=0;
  if(!flags->simdata)
  {
    if(data->path[0]=='\0')
    {
      printf("You need to provide a path to data files with --datapath\n");
      abort++;
    }
    if(data->gps[0]=='\0')
    {
      printf("You need to provide a gps start time for reading data with --trigtime\n");
      abort++;
    }
    if(data->duration[0]=='\0')
    {
      printf("You need to provide a data duration for reading data with --duration\n");
      abort++;
    }
    if(abort>0)exit(EXIT_FAILURE);
  }
  //default is to set injection from the same noise seed.
  if(data->iseed<0)data->iseed=data->nseed;
  //Report on set parameters
  fprintf(stdout,"***** RUN SETTINGS *****\n");
  fprintf(stdout,"Number of data channles ... %i\n",data->DOF);
  fprintf(stdout,"Random number seed ........ %li\n",data->seed);
  fprintf(stdout,"Injection random number seed ........ %li\n",data->iseed);
  fprintf(stdout,"******* RUN FLAGS ******\n");
  if(flags->verbose)fprintf(stdout,"Verbose flag ........ ENABLED \n");
  else              fprintf(stdout,"Verbose flag ........ DISABLED\n");
  if(flags->simdata)fprintf(stdout,"Data type is ........ SIMULATED \n");
  else
  {
    fprintf(stdout,"Data path is ........ %s \n",data->path);
    fprintf(stdout,"Data start time is .. %s \n",data->gps);
    fprintf(stdout,"Data  duration is ... %s \n",data->duration);
  }
  fprintf(stdout,"\n");

}
















