/***************************  REQUIRED LIBRARIES  ***************************/

#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <gsl/gsl_rng.h>
#include <gsl/gsl_randist.h>

#include "Subroutines.h"
#include "LISAPathfinder.h"
#include "TimePhaseMaximization.h"

/* ============================  MAIN PROGRAM  ============================ */


int main()
{
  /* declare variables */
  int i,ic,n,mc;
  int accept;
  int MCMCSTEPS;
  int BURNIN;
  int NC;

  double H;
  double alpha;

  struct Source *source;


  /* set up GSL random number generator */
  const gsl_rng_type *T = gsl_rng_default;
  gsl_rng *r = gsl_rng_alloc (T);
  gsl_rng_env_setup();

  /* Initialize data structure */
  struct Data  *data = malloc(sizeof(struct Data));

  data->T  = 1024.;
  data->dt = 0.5;
  data->df = 1.0/data->T;
  data->N  = (int)(data->T/data->dt)/2;

  data->fmin = 1.0e-4; //Hz
  data->fmax = (double)data->N/data->T;  //Hz

  data->imin = (int)floor(data->fmin*data->T);
  data->imax = (int)floor(data->fmax*data->T);

  data->d = malloc(DOF*sizeof(double *));
  data->s = malloc(DOF*sizeof(double *));
  data->n = malloc(DOF*sizeof(double *));

  for(i=0; i<DOF; i++)
  {
    data->d[i] = malloc(data->N*2*sizeof(double));
    data->s[i] = malloc(data->N*2*sizeof(double));
    data->n[i] = malloc(data->N*2*sizeof(double));
  }

  data->f = malloc(data->N*sizeof(double));

  /* Simulate noise data */
  struct Model *injection = malloc(sizeof(struct Model));
  initialize_model(injection,data->N,6);

  injection->mass = 422.0; //kg
  injection->I    = 200.0; //kg*m*m
  for(i=0; i<3; i++)
  {
    injection->Ais[i] = 2.0e-9; // m*Hz^-1/2
    injection->Ath[i] = 1.0e-8; // N*Hz^-1/2
  }

  /* Simulate source data */
  for(n=0; n<injection->N; n++)
  {
    source = injection->source[n];
    source->face = -1;
    while(source->face ==-1) draw_impact_point(data, source, r);
    printf("hit on face %i\n",source->face);
  }

  simulate_noise(data, injection, r);
  simulate_data(data);
  simulate_injection(data,injection);
  injection->logL = loglikelihood(data, injection);

  printf("Injected parameters:   \n");
  FILE *injfile = fopen("injection.dat","w");
  for(n=0; n<injection->N; n++)printf("     {%lg,%lg,%lg,%lg}\n",injection->source[n]->t0, injection->source[n]->P, injection->source[n]->costheta, injection->source[n]->phi);
  for(n=0; n<injection->N; n++)fprintf(injfile,"%lg %lg %lg %lg\n",injection->source[n]->t0, injection->source[n]->P, injection->source[n]->costheta, injection->source[n]->phi);
  fclose(injfile);
  printf("SNR of injection = %g\n",snr(data,injection));

  /* Initialize parallel chains */
  NC = 15;
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

  /* Initialize model */
  struct Model **model = malloc(NC*sizeof(struct Model*));

  struct Model *trial  = malloc(sizeof(struct Model));
  initialize_model(trial, data->N, 10);


  for(ic=0; ic<NC; ic++)
  {
    model[ic] = malloc(sizeof(struct Model));
    initialize_model(model[ic],data->N,10);

    detector_proposal(data,injection,model[ic],r);

    for(n=0; n<model[ic]->N; n++)
    {
      model[ic]->source[n]->P  = gsl_rng_uniform(r)*100;
      model[ic]->source[n]->t0 = gsl_rng_uniform(r)*data->T;

    }

    logprior(data, model[ic], injection);
    model[ic]->logL = loglikelihood(data, model[ic]);
  }

  /* set up distribution */
  //struct PSDposterior *psd = NULL;
  //setup_psd_histogram(data, injection, psd);

  /* set up MCMC run */
  accept    = 0;
  MCMCSTEPS = 100000;
  BURNIN    = MCMCSTEPS/100;//1000;

  char filename[128];

  FILE *noisechain;
  sprintf(filename,"noise.dat");
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
  for(mc=0;mc<MCMCSTEPS;mc++)
  {

    for(ic=0; ic<NC; ic++)
    {
      for(n=0; n<10; n++)
      {
        reject=0;

        //copy x to y
        copy_model(model[index[ic]], trial, data->N);

        //choose new parameters for y
        proposal(data, model[index[ic]], trial, r, &reject);

        //compute maximized likelihood
        //if(mc<BURNIN) max_loglikelihood(data, trial);

        if(reject) continue;
        else
        {
          //compute new likelihood
          trial->logL = loglikelihood(data, trial);

          //compute new prior
          logprior(data, trial, injection);

          //compute Hastings ratio
          H     = (trial->logL - model[index[ic]]->logL)/temp[index[ic]] + trial->logP - model[index[ic]]->logP;
          alpha = log(gsl_rng_uniform(r));

          //adopt new position w/ probability H
          if(H>alpha)
          {
            copy_model(trial, model[index[ic]], data->N);
            accept++;
          }
        }
      }
    }


    ptmcmc(model, temp, index, r, NC, mc);

    //cute PSD histogram
    //if(mc>MCMCSTEPS/2) populate_psd_histogram(data, model[index[0]], MCMCSTEPS, psd);

    //print chain files

    //impact parameters
    ic = index[0];
    fprintf(noisechain,"%lg ",model[ic]->logL-injection->logL);
    fprintf(noisechain,"%lg ",model[ic]->mass);
    for(i=0; i<3; i++)
    {
      fprintf(noisechain,"%lg %lg ",(injection->Ais[i]-model[ic]->Ais[0])/injection->Ais[0],(injection->Ath[0]-model[ic]->Ath[i])/injection->Ath[0]);
    }
    fprintf(noisechain,"\n");

    for(n=0; n<model[ic]->N; n++)
    {
      source = model[ic]->source[n];
      fprintf(impactchain,"%lg ",model[ic]->logL-injection->logL);
      fprintf(impactchain,"%i ",model[ic]->N);
      fprintf(impactchain,"%lg %lg %lg %lg %lg %lg %i\n", source->t0,source->P,source->map[0], source->map[1], source->costheta,source->phi,source->face);
    }


    //parallel tempering
    for(ic=0; ic<NC; ic++) fprintf(logLchain,"%lg ",model[index[ic]]->logL-injection->logL);
    for(ic=0; ic<NC; ic++) fprintf(logLchain,"%lg ",temp[ic]);
    fprintf(logLchain,"\n");





  }
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



























